from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from orion_core.queries.orion_queries import select_lap_percents


class LapProgressRepository:
    """Reads OrionDB `lap_progress` through the shared query builders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_lap_percents(
        self, run_id: str, lap_ids: list[int], start_percent: float, end_percent: float
    ) -> Sequence[Row[int, datetime, float]]:
        return (
            await self.db.execute(
                select_lap_percents(run_id, lap_ids, start_percent, end_percent)
            )
        ).all()
