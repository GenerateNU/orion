from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from orion_core.queries.orion_queries import (
    select_lap_percents_between,
    select_laps,
    select_times_by_lap_percent,
)


class LapRepository:
    """Reads OrionDB `laps` and `estimated_car_state.lap_percent` through the shared
    query builders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_lap_percents(
        self, run_id: str, start: datetime, end: datetime
    ) -> Sequence[Row[datetime, float | None]]:
        return (
            await self.db.execute(select_lap_percents_between(run_id, start, end))
        ).all()

    async def find_lap_percent_times(
        self, run_id: str, lap_id: int, start_percent: float, end_percent: float
    ) -> Row[datetime | None, datetime | None]:
        return (
            await self.db.execute(
                select_times_by_lap_percent(run_id, lap_id, start_percent, end_percent)
            )
        ).one()

    async def list_laps(self, run_id: str) -> Sequence[Row[int, datetime, datetime]]:
        return (await self.db.execute(select_laps(run_id))).all()
