from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orion_core.db.orion.models import Run


class RunRepository:
    """Queries only. Returns ORM objects or None; never raises domain errors."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self) -> Sequence[Run]:
        return (await self.db.scalars(select(Run).order_by(Run.run_id))).all()

    async def get(self, run_id: str) -> Run | None:
        return await self.db.get(Run, run_id)
