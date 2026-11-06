from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.repositories.metrics_repository import MetricsRepository
from orion_backend.schemas.metrics_schema import LapResponse, MetricsResponse


class MetricsService:
    def __init__(self, orion_db: AsyncSession):
        self.repository = MetricsRepository(orion_db)

    async def get_metrics(self, run_id: str) -> MetricsResponse:
        """Every lap for the run, in order. An unknown run comes back with no laps."""
        rows = await self.repository.list_laps(run_id)
        return MetricsResponse(
            run_id=run_id,
            laps=[
                LapResponse(lap_number=row.lap_number, start_time=row.start_time, end_time=row.end_time)
                for row in rows
            ],
        )
