from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from orion_core.models.orion import Run
from orion_core.queries.orion_queries import (
    delete_run,
    insert_run,
    select_run,
    select_run_has_pipeline_runs,
    select_runs,
    update_run,
)


class RunRepository:
    """Runs OrionDB through the shared query builders.

    Returns Run models, or None; never raises domain errors. Never commits:
    `get_orion_db` commits once per request.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_runs(self) -> Sequence[Run]:
        return (await self.db.scalars(select_runs())).all()

    async def get_run(self, run_id: str) -> Run | None:
        return (await self.db.scalars(select_run(run_id))).one_or_none()

    async def has_pipeline_runs(self, run_id: str) -> bool:
        return bool(await self.db.scalar(select_run_has_pipeline_runs(run_id)))

    async def create_run(
        self, run_id: str, start_time: datetime | None, end_time: datetime | None
    ) -> Run | None:
        """None if `run_id` already exists."""
        return await self.db.scalar(insert_run(run_id, start_time, end_time))

    async def update_run(self, run_id: str, **values: datetime | None) -> Run | None:
        """None if the run doesn't exist."""
        return await self.db.scalar(update_run(run_id, **values))

    async def delete_run(self, run_id: str) -> bool:
        """False if the run doesn't exist."""
        return await self.db.scalar(delete_run(run_id)) is not None
