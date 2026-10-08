import pandas as pd

from orion_core.queries.penelope_queries import select_readings
from orion_pipeline.clients.base_client import BaseClient


class PenelopeClient(BaseClient):
    """Read-only. Has no write methods, and its engine is opened read-only too."""

    def fetch_readings(self, run_id: str) -> pd.DataFrame:
        # TODO(#17): stream in chunks (`pd.read_sql(..., chunksize=...)`) for big runs.
        return self.read_frame(select_readings(run_id))
