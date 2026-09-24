import os
from datetime import datetime
import numpy as np 

from pydantic import ValidationError
from sqlalchemy import MetaData, create_engine, select
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from .exceptions import (
    PenelopeConfigError,
    PenelopeConnectionError,
    PenelopeSchemaError,
    PenelopeValidationError,
)
from .models import DataPoint


class PenelopeClient:
    """Read-only client for querying PenelopeDB (Postgres)."""

    def __init__(self, engine):
        """Reflect Penelope's tables off an existing SQLAlchemy engine.

        Raises:
            PenelopeConnectionError: PenelopeDB was unreachable.
            PenelopeSchemaError: Connected, but the expected tables could not
                be read.
        """
        self.engine = engine
        self.metadata = MetaData()

        # create_engine() is lazy, so this reflect() is the first time we
        # actually connect. That makes it where connection failures surface.
        try:
            self.metadata.reflect(bind=self.engine, only=["data", "data_type"])
        except OperationalError as exc:
            # Host unreachable, timeout, refused, bad password. The only
            # failure here worth retrying, which is why it gets its own type.
            raise PenelopeConnectionError(
                f"Could not connect to PenelopeDB at "
                f"{engine.url.host}:{engine.url.port}/{engine.url.database}. "
                "Check that the VPN is connected and the PENELOPE_DB_* values are correct."
            ) from exc
        except SQLAlchemyError as exc:
            # Connected, but `data`/`data_type` were not readable -- renamed
            # table, wrong search_path, or a missing grant. Retrying cannot
            # help, so this is a schema error rather than a connection one.
            # Must come second: OperationalError is a SQLAlchemyError subclass.
            raise PenelopeSchemaError(
                "Connected to PenelopeDB but could not reflect tables `data` and "
                "`data_type`. Check that they exist and the role has SELECT on them."
            ) from exc

        self.data_table = self.metadata.tables["data"]
        self.data_type_table = self.metadata.tables["data_type"]

    @classmethod
    def from_env(cls) -> "PenelopeClient":
        """Build a client from PENELOPE_DB_HOST/PORT/NAME/USER/PASSWORD env vars.

        Raises:
            PenelopeConfigError: A required env var is missing or blank.
        """
        required = (
            "PENELOPE_DB_USER",
            "PENELOPE_DB_PASSWORD",
            "PENELOPE_DB_HOST",
            "PENELOPE_DB_PORT",
            "PENELOPE_DB_NAME",
        )
        # Collect all missing vars before raising
        # If empty, raise a ConfigError message
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            raise PenelopeConfigError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Set them in your .env file."
            )

        url = (
            f"postgresql+psycopg2://{os.environ['PENELOPE_DB_USER']}:"
            f"{os.environ['PENELOPE_DB_PASSWORD']}@{os.environ['PENELOPE_DB_HOST']}:"
            f"{os.environ['PENELOPE_DB_PORT']}/{os.environ['PENELOPE_DB_NAME']}"
        )
        return cls(create_engine(url))

    def _to_array(self, rows) -> np.ndarray:
        """Convert raw `data` rows into a NumPy 2D array.

        Columns: [time, dataTypeName, runId, values]

        Raises:
            PenelopeValidationError: A row did not match the expected shape.
        """

        validated_rows = []
        for index, row in enumerate(rows):
            mapping = dict(row._mapping)
            try:
                point = DataPoint(**mapping)
            except ValidationError as exc:
                raise PenelopeValidationError(
                    f"Row {index} did not match DataPoint "
                    f"(runId={mapping.get('runId')!r}, time={mapping.get('time')!r}). "
                    "Penelope's schema may have changed."
                ) from exc
            validated_rows.append([point.time, point.dataTypeName, point.runId, point.values])
            
        return np.array(validated_rows, dtype=object)

    def _fetch(self, stmt) -> np.ndarray:
        """Run a SELECT against Penelope and convert the rows to DataPoints.

        Shared by every query method so the connection handling lives in one
        place instead of being repeated per query.

        Raises:
            PenelopeConnectionError: The connection failed or dropped mid-query.
            PenelopeSchemaError: The `data` table could not be read.
        """
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(stmt).fetchall()
        except OperationalError as exc:
            # The engine pools connections, so one can go stale between
            # building the client and running a query. A VPN drop mid-session
            # lands here rather than in __init__, and is still retryable.
            raise PenelopeConnectionError(
                f"Lost connection to PenelopeDB at {self.engine.url.host}:"
                f"{self.engine.url.port}. Check that the VPN is still connected."
            ) from exc
        except SQLAlchemyError as exc:
            # Reflection only reads the catalog, so a role that can see `data`
            # but lacks SELECT on it gets past __init__ and fails here instead.
            raise PenelopeSchemaError(
                "Query against PenelopeDB failed. Check that the connecting role "
                "has SELECT on `data`."
            ) from exc
        return self._to_array(rows)

    def get_all(self) -> np.ndarray:
        """Fetch every row in `data`.

        Raises:
            PenelopeConnectionError: PenelopeDB was unreachable.
            PenelopeSchemaError: The `data` table could not be read.
            PenelopeValidationError: A row did not match DataPoint.
        """
        return self._fetch(select(self.data_table))

    def get_by_run_id(self, run_id: str) -> np.ndarray:
        """Fetch all `data` rows for a single run.

        Raises:
            PenelopeConnectionError: PenelopeDB was unreachable.
            PenelopeSchemaError: The `data` table could not be read.
            PenelopeValidationError: A row did not match DataPoint.
        """
        stmt = select(self.data_table).where(self.data_table.c.runId == run_id)
        return self._fetch(stmt)

    def get_by_time_bounds(self, start: datetime, end: datetime) -> np.ndarray:
        """Fetch all `data` rows with `time` between start and end (inclusive).

        Raises:
            PenelopeConnectionError: PenelopeDB was unreachable.
            PenelopeSchemaError: The `data` table could not be read.
            PenelopeValidationError: A row did not match DataPoint.
        """
        stmt = select(self.data_table).where(
            self.data_table.c.time >= start, self.data_table.c.time <= end
        )
        return self._fetch(stmt)

    def get_all_paginated(self, batch_size: int = 5000):

      """Yields batches of rows as NumPy arrays, using cursor pagination on `time`."""
      last_time = None
      while True:

            # LIMIT keeps each page a fixed, bounded size.
            stmt = select(self.data_table).order_by(self.data_table.c.time).limit(batch_size)

            # First page has no cursor yet. Every page after that starts after last row is yielded
            if last_time is not None:
                stmt = stmt.where(self.data_table.c.time > last_time)

            with self.engine.connect() as conn:
                rows = conn.execute(stmt).fetchall()

            if not rows: 
                break

            # hand this page off before fetching the next one so the whole table is never held in memory at once.
            yield self._to_array(rows)
            last_time = rows[-1].time