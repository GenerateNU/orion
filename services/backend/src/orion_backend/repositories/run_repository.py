from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from orion_core.models.orion import Run
from orion_core.queries.orion_queries import select_run, select_runs


class RunRepository:
    """Runs OrionDB through the shared query builders.

    Returns Run models, or None; never raises domain errors.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_runs(self) -> Sequence[Run]:
        return (await self.db.scalars(select_runs())).all()

    async def get_run(self, run_id: str) -> Run | None:
        return (await self.db.scalars(select_run(run_id))).one_or_none()
