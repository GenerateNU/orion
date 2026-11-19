import logging
from collections.abc import Iterator
from datetime import datetime
from typing import Any, cast

import pandas as pd
import psycopg
from psycopg import sql
from sqlalchemy import Connection, delete

from orion_core.models import Base
from orion_core.queries.orion_queries import select_sensor_sources, update_run
from orion_pipeline.clients.base_client import BaseClient

logger = logging.getLogger(__name__)


class OrionDBClient(BaseClient):
    """The only client steps write through."""

    def read_sensor_map(self) -> dict[str, str]:
        """Penelope raw tag -> generic sensor name, from `sensor_sources`."""
        df = self.read_frame(select_sensor_sources())
        return dict(zip(df["raw_tag"], df["sensor"], strict=True))

    def set_run_bounds(
        self, run_id: str, start_time: datetime | None, end_time: datetime | None
    ) -> None:
        """Write the run's first and last reading times to `runs`."""
        with self.engine.begin() as conn:
            conn.execute(update_run(run_id, start_time=start_time, end_time=end_time))
        logger.info("run %s bounds: %s -> %s", run_id, start_time, end_time)

    def delete_for_run(self, table: str, run_id: str) -> None:
        """Delete all of `run_id`'s rows in `table`.

        Called once before a step writes its first page, so that re-runs
        replace the run's rows instead of duplicating them.
        """
        target = Base.metadata.tables[table]
        with self.engine.begin() as conn:
            deleted = conn.execute(delete(target).where(target.c.run_id == run_id))
        logger.info("deleted %d rows in %s for run %s", deleted.rowcount, table, run_id)

    def append(self, table: str, df: pd.DataFrame) -> None:
        """Append one page of rows to `table` with Postgres COPY, in its own transaction."""
        if df.empty:
            return
        with self.engine.begin() as conn:
            _copy(conn, table, df)
        logger.info("wrote %d rows to %s", len(df), table)


def _raw(conn: Connection) -> psycopg.Connection[Any]:
    """The psycopg connection under a SQLAlchemy one, for COPY and raw SQL."""
    return cast(psycopg.Connection[Any], conn.connection.driver_connection)


def _copy(conn: Connection, table: str, df: pd.DataFrame) -> None:
    """COPY `df`'s rows into `table` on `conn`'s transaction."""
    copy_sql = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, df.columns)),
    )
    with _raw(conn).cursor() as cur, cur.copy(copy_sql) as copy:
        for row in _rows(df):
            copy.write_row(row)


def _rows(df: pd.DataFrame) -> Iterator[tuple[Any, ...]]:
    """`df`'s rows as Python values psycopg can adapt, with NaN as None (NULL)."""
    # astype(object) turns numpy scalars into Python ones; where() swaps NaN for None.
    values = df.astype(object)
    return values.where(values.notna(), None).itertuples(index=False, name=None)
