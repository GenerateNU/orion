from collections.abc import Iterator

import pandas as pd

from orion_core.queries.penelope_queries import select_readings
from orion_pipeline.clients.base_client import BaseClient


class PenelopeClient(BaseClient):
    """Read-only. Has no write methods, and its engine is opened read-only too."""

    def iter_readings(
        self, run_id: str, key: tuple[str, ...], page_size: int
    ) -> Iterator[pd.DataFrame]:
        return self.iter_pages(select_readings(run_id), key, page_size)
