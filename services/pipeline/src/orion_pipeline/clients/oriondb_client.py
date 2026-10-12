import logging

import pandas as pd

from orion_pipeline.clients.base_client import BaseClient

logger = logging.getLogger(__name__)


class OrionDBClient(BaseClient):
    """The only client steps write through."""

    def delete_for_run(self, table: str, run_id: str) -> None:
        """Delete all of `run_id`'s rows in `table`.

        Called once before a step writes its first page, so that re-runs
        replace the run's rows instead of duplicating them.

        TODO: DELETE FROM `table` WHERE run_id = `run_id`.
        """
        logger.info("would delete rows in %s for run %s", table, run_id)

    def append(self, table: str, df: pd.DataFrame) -> None:
        """Append one page of rows to `table`.

        TODO: bulk-insert `df` (Postgres COPY) in its own transaction.
        """
        logger.info("would write %d rows to %s", len(df), table)
