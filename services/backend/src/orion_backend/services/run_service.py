from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import NotFoundError
from orion_backend.repositories.run_repository import RunRepository
from orion_backend.schemas.run_schema import RunResponse


class RunService:
    """Business rules live here: e.g. turning "no row" into a NotFoundError."""

    def __init__(self, db: AsyncSession):
        self.repository = RunRepository(db)

    async def list_runs(self) -> list[RunResponse]:
        return [RunResponse.model_validate(run) for run in await self.repository.list()]

    async def get_run(self, run_id: str) -> RunResponse:
        run = await self.repository.get(run_id)
        if run is None:
            raise NotFoundError("Run", run_id)
        return RunResponse.model_validate(run)
