from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import InvalidParameterError
from orion_backend.repositories.lap_progress_repository import LapProgressRepository
from orion_backend.repositories.lap_repository import LapRepository
from orion_backend.repositories.state_repository import StateRepository
from orion_backend.schemas.state_schema import StateDataResponse


class StateService:
    def __init__(self, orion_db: AsyncSession):
        self.repository = StateRepository(orion_db)
        self.laps = LapRepository(orion_db)
        self.lap_progress = LapProgressRepository(orion_db)

    async def get_state_data(self, run_id: str, start: datetime, end: datetime) -> StateDataResponse:
        """Every estimated position in `[start, end]`, ascending by time.

        An unknown run or an empty range comes back with empty lists.
        """
        if start > end:
            raise InvalidParameterError("`start` must be at or before `end`")

        rows = await self.repository.list_positions(run_id, start, end)
        # `lap_progress` has one row per position, at the same time: read the laps
        # that overlap [start, end] and look each position up by its time.
        laps = await self.laps.list_laps(run_id)
        lap_ids = [lap.lap_id for lap in laps if lap.start_time <= end and lap.end_time >= start]
        lap_rows = (
            await self.lap_progress.list_lap_percents(run_id, lap_ids, 0, 100) if lap_ids else []
        )
        percents = {row.time: row.lap_percent for row in lap_rows}
        return StateDataResponse(
            run_id=run_id,
            start=start,
            end=end,
            time=[row.time for row in rows],
            positions=[(row.lattitude, row.longitude) for row in rows],
            lap_percent=[percents.get(row.time) for row in rows],
        )
