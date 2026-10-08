from collections.abc import Sequence

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from orion_core.queries.penelope_queries import select_readings


class ReadingRepository:
    """Reads Penelope (or penelope2) through the shared query builders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, run_id: str, limit: int) -> Sequence[Row]:
        return (await self.db.execute(select_readings(run_id, limit))).all()
