from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from orion_core.models.orion import Lap
from orion_core.queries.orion_queries import select_laps


class LapRepository:
    """Reads OrionDB `laps` through the shared query builders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_laps(self, run_id: str) -> Sequence[Lap]:
        return (await self.db.scalars(select_laps(run_id))).all()
