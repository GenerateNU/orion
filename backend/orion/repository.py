import math
from contextlib import contextmanager
from typing import Any, Generic, Iterator, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError
from sqlalchemy import Table, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from .exceptions import OrionConnectionError, OrionSchemaError, OrionValidationError
from .schema import data_table
from penelope.models import DataPoint

ModelT = TypeVar("ModelT", bound=BaseModel)


def _same(a: Any, b: Any) -> bool:
    """Exact equality, except that NaN is considered equal to itself.

    Plain `==` cannot be used to compare a record against its stored copy.
    IEEE 754 leaves NaN unordered with everything including itself, and
    penelope.models documents that NaN readings are passed through rather
    than filtered, so a `values` array containing one would never equal
    itself after a round trip. Python's container shortcut (`x is y or
    x == y`) only rescues the case where both sides are the same object,
    which a row read back out of Postgres never is.

    Deliberately exact everywhere else -- no float tolerance. The point of
    verify() is to catch corruption, and a tolerance would hide exactly the
    small drifts worth knowing about.
    """
    if isinstance(a, float) and isinstance(b, float):
        return a == b or (math.isnan(a) and math.isnan(b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


class Repository(Generic[ModelT]):
    """Generic write-only repository: one Pydantic model <-> one Table.

    Subclasses supply the model/table pair; everything here is driven off the
    table's own primary key, so a new table needs no new query logic.
    """

    def __init__(self, engine: Engine, model: Type[ModelT], table: Table):
        self.engine = engine
        self.model = model
        self.table = table
        self._pk_columns = list(table.primary_key.columns)

    def _to_row(self, record: Union[ModelT, dict]) -> dict:
        """Validate one record and render it as a row dict.

        Raises:
            ValidationError: The record does not satisfy the model.
        """
        # Pydantic defaults to revalidate_instances='never', so calling
        # model_validate() on something that is already an instance of the
        # model hands it back untouched -- a DataPoint built with
        # model_construct(), which skips validation entirely, would sail
        # through. Dumping to a dict first forces the validators to run, so
        # the guarantee here is "validated", not merely "right class".
        # warnings=False because this dump exists only to feed the validator;
        # if the record is malformed, Pydantic's serializer would emit a
        # UserWarning about each bad field just before model_validate raises a
        # ValidationError naming the same fields properly.
        payload = (
            record.model_dump(warnings=False)
            if isinstance(record, BaseModel)
            else record
        )
        return self.model.model_validate(payload).model_dump(by_alias=True)

    @contextmanager
    def _translating_db_errors(self, operation: str) -> Iterator[None]:
        """Re-raise SQLAlchemy failures from `operation` as Orion types.

        Keeps the library boundary at this module, so callers handle
        OrionError and never import sqlalchemy.exc to catch a dead
        connection. Orion's own exceptions pass through untouched.
        """
        url = self.engine.url
        where = f"{url.host}/{url.database}"
        try:
            yield
        except IntegrityError as exc:
            # The primary key is already absorbed by ON CONFLICT DO NOTHING,
            # so a constraint violation that reaches here is one the model
            # does not know about -- model and table disagree on what is valid.
            raise OrionValidationError(
                f"OrionDB refused a row for `{self.table.name}` that "
                f"{self.model.__name__} accepted, so the model is missing a "
                f"constraint the table enforces: {exc.orig}"
            ) from exc
        except OperationalError as exc:
            raise OrionConnectionError(
                f"Could not reach OrionDB at {where} to {operation} "
                f"`{self.table.name}`. A Neon endpoint may have autosuspended, "
                f"in which case retrying should wake it: {exc.orig}"
            ) from exc
        except SQLAlchemyError as exc:
            # Must come last: OperationalError and IntegrityError are both
            # SQLAlchemyError subclasses, so a broad clause above would
            # swallow them.
            raise OrionSchemaError(
                f"Connected to OrionDB at {where} but could not {operation} "
                f"`{self.table.name}`. Check that the table exists "
                f"(setup_orion.py creates it) and the role has access: {exc}"
            ) from exc

    def _key(self, record: ModelT) -> tuple:
        """The record's primary key, as a tuple in table column order.

        Raises:
            OrionSchemaError: A primary key column has no matching field on
                the model.
        """
        try:
            return tuple(getattr(record, c.name) for c in self._pk_columns)
        except AttributeError as exc:
            # Only reachable from a subclass whose model and table were paired
            # with mismatched names. Left bare, it surfaces as an AttributeError
            # from inside verify() with nothing to say why.
            raise OrionSchemaError(
                f"`{self.table.name}` has a primary key column with no matching "
                f"field on {self.model.__name__} ({exc}). The two must agree on "
                "column names for this repository to address rows."
            ) from exc

    def write(self, record: ModelT) -> int:
        """Insert one record. See write_many for behaviour and errors."""
        return self.write_many([record])

    def write_many(self, records: list[ModelT]) -> int:
        """Insert records, skipping any whose primary key is already present.

        Returns:
            The number of rows actually inserted. Anything short of
            len(records) is the count that already existed.

        Raises:
            OrionValidationError: A record does not satisfy the model, or the
                database refused a row the model accepted. Nothing is written
                in either case -- see below.
            OrionConnectionError: OrionDB was unreachable.
            OrionSchemaError: Connected, but the insert could not be run.
        """
        if not records:
            return 0

        # Validate the whole batch before opening a connection. A single bad
        # record then means nothing at all is written, rather than a partial
        # batch landing before the bad one is reached.
        #
        # Because that discards everything, the error has to name the record
        # responsible: an ingest batch is thousands of points wide, and
        # Pydantic's own message describes the offending fields without saying
        # which of the thousands they belong to.
        rows = []
        for i, record in enumerate(records):
            try:
                rows.append(self._to_row(record))
            except ValidationError as exc:
                raise OrionValidationError(
                    f"Record {i} of {len(records)} is not a valid "
                    f"{self.model.__name__}, so none of the batch was "
                    f"written:\n{exc}"
                ) from exc

        # ON CONFLICT DO NOTHING makes re-ingest a no-op instead of an error.
        # Without it, re-pulling a window that is already stored would raise
        # IntegrityError against the primary key and lose the genuinely new
        # rows in the same batch.
        #
        # The tradeoff: DO NOTHING keeps the row Orion already has. If Penelope
        # ever corrects a reading in place, that correction will not propagate
        # -- switch to on_conflict_do_update() if Penelope's rows are mutable.
        stmt = insert(self.table).on_conflict_do_nothing()
        with self._translating_db_errors("insert into"):
            with self.engine.begin() as conn:
                return conn.execute(stmt, rows).rowcount

    def verify(self, records: list[ModelT], chunk_size: int = 1000) -> list[ModelT]:
        """Read records back out and report any the database does not match.

        The repository is otherwise write-only; this reads purely to confirm
        that what landed in Orion equals what came out of the source. An empty
        result means every record is stored exactly as given.

        Returns:
            The records that are missing from the table or differ from it.

        Raises:
            OrionConnectionError: OrionDB was unreachable.
            OrionSchemaError: Connected, but the rows could not be read, or
                the model and table disagree about column names.
            OrionValidationError: A stored row would not parse back into the
                model, meaning the table has drifted from the code.
        """
        if not records:
            return []

        expected = {self._key(r): r for r in records}
        found: dict[tuple, ModelT] = {}

        # Fetch by primary key in chunks. One query per record would be tens of
        # thousands of round trips; a single query would build an unbounded
        # IN clause.
        keys = list(expected)
        with self._translating_db_errors("read from"):
            with self.engine.connect() as conn:
                for i in range(0, len(keys), chunk_size):
                    stmt = select(self.table).where(
                        tuple_(*self._pk_columns).in_(keys[i:i + chunk_size])
                    )
                    for row in conn.execute(stmt).mappings():
                        try:
                            stored = self.model.model_validate(dict(row))
                        except ValidationError as exc:
                            # Distinct from the write-side failure: this row
                            # was already accepted once, so the table and the
                            # model have diverged since it was stored.
                            raise OrionValidationError(
                                f"A row stored in `{self.table.name}` no longer "
                                f"parses into {self.model.__name__}, so the "
                                f"table has drifted from the code:\n{exc}"
                            ) from exc
                        found[self._key(stored)] = stored

        # Compares every field, so this catches a truncated values array or a
        # shifted timestamp, not just a missing row.
        return [
            record
            for key, record in expected.items()
            if not self._matches(record, found.get(key))
        ]

    def _matches(self, record: ModelT, stored: Optional[ModelT]) -> bool:
        """Whether a stored row reproduces the record it came from."""
        if stored is None:
            return False
        return _same(record.model_dump(), stored.model_dump())


class DataPointRepository(Repository[DataPoint]):
    """Write-only repository for the `data` table."""

    def __init__(self, engine: Engine):
        super().__init__(engine, DataPoint, data_table)
