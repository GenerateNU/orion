from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.repositories.penelope_run_repository import PenelopeRunRepository
from orion_backend.repositories.run_repository import RunRepository
from orion_backend.schemas.penelope_run_schema import PenelopeRunResponse


class PenelopeRunService:
    def __init__(self, penelope_db: AsyncSession, orion_db: AsyncSession):
        self.repository = PenelopeRunRepository(penelope_db)
        self.run_repository = RunRepository(orion_db)

    async def list_runs(self) -> list[PenelopeRunResponse]:
        """Every Penelope run, newest first, flagged if Orion has processed it."""
        processed = await self.run_repository.list_processed_run_ids()
        return [
            PenelopeRunResponse(
                run_id=row.run_id,
                time=row.time,
                processed=row.run_id in processed,
            )
            for row in await self.repository.list_runs()
        ]
