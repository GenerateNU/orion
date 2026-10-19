from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from orion_core.queries.orion_queries import select_estimated_positions_between


class StateRepository:
    """Reads OrionDB `estimated_car_state` through the shared query builders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_positions(
        self, run_id: str, start: datetime, end: datetime
    ) -> Sequence[Row[datetime, float, float]]:
        return (await self.db.execute(select_estimated_positions_between(run_id, start, end))).all()
