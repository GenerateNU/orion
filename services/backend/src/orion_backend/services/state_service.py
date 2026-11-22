from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import InvalidParameterError
from orion_backend.repositories.lap_repository import LapRepository
from orion_backend.repositories.state_repository import StateRepository
from orion_backend.schemas.state_schema import StateDataResponse


class StateService:
    def __init__(self, orion_db: AsyncSession):
        self.repository = StateRepository(orion_db)
        self.laps = LapRepository(orion_db)

    async def get_state_data(self, run_id: str, start: datetime, end: datetime) -> StateDataResponse:
        """Every estimated position in `[start, end]`, ascending by time.

        An unknown run or an empty range comes back with empty lists.
        """
        if start > end:
            raise InvalidParameterError("`start` must be at or before `end`")

        rows = await self.repository.list_positions(run_id, start, end)
        # `lap_progress` has one row per position, at the same time.
        percents = dict(await self.laps.list_lap_percents(run_id, start, end))
        return StateDataResponse(
            run_id=run_id,
            start=start,
            end=end,
            time=[row.time for row in rows],
            positions=[(row.lattitude, row.longitude) for row in rows],
            lap_percent=[percents.get(row.time) for row in rows],
        )
