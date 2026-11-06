from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from orion_core.queries.orion_queries import select_laps


class MetricsRepository:
    """Reads OrionDB `metrics` through the shared query builders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_laps(self, run_id: str) -> Sequence[Row[int, datetime, datetime]]:
        return (await self.db.execute(select_laps(run_id))).all()
