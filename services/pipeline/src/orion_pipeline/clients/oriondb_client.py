import logging

import pandas as pd

from orion_pipeline.clients.base_client import BaseClient

logger = logging.getLogger(__name__)


class OrionDBClient(BaseClient):
    """The only client steps write through."""

    def replace_for_run(self, table: str, run_id: str, df: pd.DataFrame) -> None:
        """Replace all of `run_id`'s rows in `table` with `df`.

        TODO: in ONE transaction, DELETE the run's rows then bulk-insert `df`
        (Postgres COPY). Replacing instead of appending makes re-runs safe.
        """
        logger.info("would write %d rows to %s for run %s", len(df), table, run_id)
