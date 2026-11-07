from bisect import bisect_left
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import InvalidParameterError, NotFoundError
from orion_backend.lap_progress import lap_progress, reference_lap
from orion_backend.repositories.lap_repository import LapRepository
from orion_backend.repositories.state_repository import StateRepository
from orion_backend.schemas.lap_progress_schema import LapProgressResponse


class LapProgressService:
    def __init__(self, orion_db: AsyncSession):
        self.lap_repository = LapRepository(orion_db)
        self.state_repository = StateRepository(orion_db)

    async def get_lap_progress(
        self, run_id: str, start: datetime, end: datetime
    ) -> LapProgressResponse:
        """Lap progress for every estimated position in `[start, end]` that falls in
        a lap, ascending by time.

        An empty range comes back with empty lists. A run with no laps, or whose
        reference lap has no positions, raises NotFoundError.
        """
        if start > end:
            raise InvalidParameterError("`start` must be at or before `end`")

        laps = await self.lap_repository.list_laps(run_id)
        if not laps:
            raise NotFoundError("Laps for run", run_id)
        reference = reference_lap(laps)
        reference_rows = [
            row
            for row in await self.state_repository.list_positions(
                run_id, reference.start_time, reference.end_time
            )
            if row.time < reference.end_time
        ]
        if not reference_rows:
            raise NotFoundError("Data for lap", reference.lap_id)
        ref_lat = [row.lattitude for row in reference_rows]
        ref_lon = [row.longitude for row in reference_rows]

        rows = await self.state_repository.list_positions(run_id, start, end)
        times = [row.time for row in rows]
        response = LapProgressResponse(run_id=run_id, start=start, end=end)
        for lap in laps:
            in_lap = rows[
                bisect_left(times, lap.start_time) : bisect_left(times, lap.end_time)
            ]
            if not in_lap:
                continue
            lat = [row.lattitude for row in in_lap]
            lon = [row.longitude for row in in_lap]
            response.time += [row.time for row in in_lap]
            response.progress += lap_progress(lat, lon, ref_lat, ref_lon).tolist()
        return response
