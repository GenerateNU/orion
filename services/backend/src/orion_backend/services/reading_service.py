from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.repositories.reading_repository import ReadingRepository
from orion_backend.schemas.reading_schema import ReadingResponse


class ReadingService:
    def __init__(self, penelope_db: AsyncSession):
        self.repository = ReadingRepository(penelope_db)

    async def list_readings(self, run_id: str, limit: int) -> list[ReadingResponse]:
        # TODO: the signal explorer (clean names, time window, x-axis = position,
        # downsampling) goes here. See docs/REFACTOR_PLAN.md §4.
        rows = await self.repository.list(run_id, limit)
        return [ReadingResponse.model_validate(row) for row in rows]
