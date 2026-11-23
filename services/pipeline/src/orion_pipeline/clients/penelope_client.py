from collections.abc import Collection, Iterator

import pandas as pd

from orion_core.queries.penelope_queries import select_penelope_runs, select_readings
from orion_pipeline.clients.base_client import BaseClient


class PenelopeClient(BaseClient):
    """Read-only. Has no write methods, and its engine is opened read-only too."""

    def iter_readings(
        self,
        run_id: str,
        key: tuple[str, ...],
        data_type_names: Collection[str] | None = None,
    ) -> Iterator[pd.DataFrame]:
        return self.iter_pages(
            select_readings(run_id, data_type_names=data_type_names), key
        )

    def read_run_readings(
        self, run_id: str, data_type_names: Collection[str]
    ) -> pd.DataFrame:
        """Every reading of the given raw tags for the whole run, in one frame.

        Still read page by page, so each query stays short. Only for a few tags:
        the whole result is held in memory.
        """
        pages = list(self.iter_readings(run_id, ("time", "raw_tag"), data_type_names))
        if not pages:
            return pd.DataFrame(columns=["time", "raw_tag", "values"])
        return pd.concat(pages, ignore_index=True)

    def list_runs(self) -> pd.DataFrame:
        """Every Penelope run, newest first: `run_id` (uuid) and `time`."""
        return self.read_frame(select_penelope_runs())
