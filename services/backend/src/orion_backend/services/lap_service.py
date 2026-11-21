from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.repositories.lap_repository import LapRepository
from orion_backend.schemas.lap_schema import LapResponse, LapsResponse


class LapService:
    def __init__(self, orion_db: AsyncSession):
        self.repository = LapRepository(orion_db)

    async def get_laps(self, run_id: str) -> LapsResponse:
        """Every lap of the run, in order. An unknown run has no laps."""
        rows = await self.repository.list_laps(run_id)
        return LapsResponse(
            run_id=run_id,
            laps=[
                LapResponse(
                    lap_id=row.lap_id, start_time=row.start_time, end_time=row.end_time
                )
                for row in rows
            ],
        )
