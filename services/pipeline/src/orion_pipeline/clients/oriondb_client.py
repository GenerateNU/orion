import logging
from collections.abc import Iterator
from datetime import datetime
from typing import Any, cast

import pandas as pd
import psycopg
from psycopg import sql
from sqlalchemy import Connection, delete, update

from orion_core.models import Base
from orion_core.queries.orion_queries import select_sensor_sources, update_run
from orion_pipeline.clients.base_client import BaseClient

logger = logging.getLogger(__name__)

# Staging table for `update_for_run`, dropped when its transaction commits.
UPDATES_TABLE = "_updates"


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

    def set_null_for_run(self, table: str, column: str, run_id: str) -> None:
        """Set `column` to NULL on all of `run_id`'s rows in `table`.

        The counterpart of `delete_for_run` for steps that fill in a column of
        another step's table, so a re-run replaces the values.
        """
        target = Base.metadata.tables[table]
        with self.engine.begin() as conn:
            cleared = conn.execute(
                update(target).where(target.c.run_id == run_id).values({column: None})
            )
        logger.info(
            "cleared %s on %d rows in %s for run %s",
            column,
            cleared.rowcount,
            table,
            run_id,
        )

    def append(self, table: str, df: pd.DataFrame) -> None:
        """Append one page of rows to `table` with Postgres COPY, in its own transaction."""
        if df.empty:
            return
        with self.engine.begin() as conn:
            _copy(conn, table, df)
        logger.info("wrote %d rows to %s", len(df), table)

    def update_for_run(self, table: str, run_id: str, df: pd.DataFrame) -> None:
        """Set `df`'s columns other than `time` on `run_id`'s rows of `table`,
        matched by `time`. NaN is written as NULL.

        The rows are copied into a temporary table and applied with one
        `UPDATE ... FROM`, in a single transaction.
        """
        if df.empty:
            return
        columns = [c for c in df.columns if c != "time"]
        target, staging = sql.Identifier(table), sql.Identifier(UPDATES_TABLE)
        create = sql.SQL(
            "CREATE TEMP TABLE {} ON COMMIT DROP AS SELECT {} FROM {} WITH NO DATA"
        ).format(
            staging,
            sql.SQL(", ").join(map(sql.Identifier, ["time", *columns])),
            target,
        )
        apply = sql.SQL(
            "UPDATE {} AS t SET {} FROM {} AS u WHERE t.run_id = %s AND t.time = u.time"
        ).format(
            target,
            sql.SQL(", ").join(
                sql.SQL("{} = u.{}").format(sql.Identifier(c), sql.Identifier(c))
                for c in columns
            ),
            staging,
        )
        with self.engine.begin() as conn:
            with _raw(conn).cursor() as cur:
                cur.execute(create)
            _copy(conn, UPDATES_TABLE, df[["time", *columns]])
            with _raw(conn).cursor() as cur:
                cur.execute(apply, (run_id,))
                updated = cur.rowcount
        logger.info("updated %d rows in %s for run %s", updated, table, run_id)


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
