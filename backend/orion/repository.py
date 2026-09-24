from typing import Generic, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from .schema import data_table
from penelope.models import DataPoint

ModelT = TypeVar("ModelT", bound=BaseModel)


class Repository(Generic[ModelT]):
    """Generic write-only repository: one Pydantic model <-> one Table."""

    def __init__(self, engine: Engine, model: Type[ModelT], table: Table):
        self.engine = engine
        self.model = model
        self.table = table

    def write(self, record: ModelT) -> int:
        return self.write_many([record])

    def write_many(self, records: list[ModelT]) -> int:
        """Insert records, skipping any whose primary key is already stored.

        Returns the number of rows actually inserted.
        """
        if not records:
            return 0
        for r in records:
            if not isinstance(r, self.model):
                raise TypeError(f"expected {self.model.__name__}, got {type(r).__name__}")
        rows =[r.model_dump(by_alias=True) for r in records]
        # ON CONFLICT DO NOTHING lets overlapping pulls be re-written without
        # erroring or duplicating rows. Existing rows are kept as-is.
        stmt = insert(self.table).on_conflict_do_nothing()
        with self.engine.begin() as conn:
            return conn.execute(stmt, rows).rowcount


class DataPointRepository(Repository[DataPoint]):
    """Write-only repository for the `data` table."""

    def __init__(self, engine: Engine):
        super().__init__(engine, DataPoint, data_table)
