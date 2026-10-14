import logging

import pandas as pd
from psycopg import sql
from sqlalchemy import delete

from orion_core.models import Base
from orion_core.queries.orion_queries import select_sensor_sources
from orion_pipeline.clients.base_client import BaseClient

logger = logging.getLogger(__name__)


class OrionDBClient(BaseClient):
    """The only client steps write through."""

    def read_sensor_map(self) -> dict[str, str]:
        """Penelope raw tag -> generic sensor name, from `sensor_sources`."""
        df = self.read_frame(select_sensor_sources())
        return dict(zip(df["raw_tag"], df["sensor"]))

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
        copy_sql = sql.SQL("COPY {} ({}) FROM STDIN").format(
            sql.Identifier(table),
            sql.SQL(", ").join(map(sql.Identifier, df.columns)),
        )
        # astype(object) turns numpy scalars into Python ones psycopg can adapt.
        rows = df.astype(object).itertuples(index=False, name=None)
        with self.engine.begin() as conn:
            with conn.connection.cursor() as cur, cur.copy(copy_sql) as copy:
                for row in rows:
                    copy.write_row(row)
        logger.info("wrote %d rows to %s", len(df), table)
