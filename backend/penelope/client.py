import os
from datetime import datetime

from sqlalchemy import MetaData, create_engine, select

from .models import DataPoint


class PenelopeClient:
    """Read-only client for querying PenelopeDB (Postgres)."""

    def __init__(self, engine):
        self.engine = engine
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine, only=["data", "data_type"])
        self.data_table = self.metadata.tables["data"]
        self.data_type_table = self.metadata.tables["data_type"]

    @classmethod
    def from_env(cls) -> "PenelopeClient":
        """Build a client from PENELOPE_DB_HOST/PORT/NAME/USER/PASSWORD env vars."""
        url = (
            f"postgresql+psycopg2://{os.environ['PENELOPE_DB_USER']}:"
            f"{os.environ['PENELOPE_DB_PASSWORD']}@{os.environ['PENELOPE_DB_HOST']}:"
            f"{os.environ.get('PENELOPE_DB_PORT', '5432')}/{os.environ['PENELOPE_DB_NAME']}"
        )
        return cls(create_engine(url))

    def _to_datapoints(self, rows) -> list[DataPoint]:
        return [DataPoint(**dict(row._mapping)) for row in rows]

    def get_all(self) -> list[DataPoint]:
        """Fetch every row in `data`."""
        with self.engine.connect() as conn:
            rows = conn.execute(select(self.data_table)).fetchall()
        return self._to_datapoints(rows)

    def get_by_run_id(self, run_id: str) -> list[DataPoint]:
        """Fetch all `data` rows for a single run."""
        with self.engine.connect() as conn:
            stmt = select(self.data_table).where(self.data_table.c.runId == run_id)
            rows = conn.execute(stmt).fetchall()
        return self._to_datapoints(rows)

    def get_by_time_bounds(self, start: datetime, end: datetime) -> list[DataPoint]:
        """Fetch all `data` rows with `time` between start and end (inclusive)."""
        with self.engine.connect() as conn:
            stmt = select(self.data_table).where(
                self.data_table.c.time >= start, self.data_table.c.time <= end
            )
            rows = conn.execute(stmt).fetchall()
        return self._to_datapoints(rows)