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

    def list_runs(self) -> pd.DataFrame:
        """Every Penelope run, newest first: `run_id` (uuid) and `time`."""
        return self.read_frame(select_penelope_runs())
