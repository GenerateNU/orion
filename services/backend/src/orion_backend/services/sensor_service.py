from bisect import bisect_left
from datetime import UTC, datetime, timedelta

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import InvalidParameterError, NotFoundError
from orion_backend.repositories.lap_progress_repository import LapProgressRepository
from orion_backend.repositories.sensor_repository import SensorRepository
from orion_backend.schemas.sensor_schema import (
    LapSensorDataResponse,
    LapSensorSeries,
    SensorDataResponse,
    SensorResponse,
    SensorSeries,
)
from orion_core.db.sensor_catalog import lagged_raw_tags
from orion_core.settings import get_settings


class SensorService:
    def __init__(self, penelope_db: AsyncSession, orion_db: AsyncSession):
        self.repository = SensorRepository(penelope_db)
        self.lap_progress = LapProgressRepository(orion_db)
        self.offset = timedelta(seconds=get_settings().gps_time_offset_s)
        self.lagged = lagged_raw_tags()

    async def list_sensors(self) -> list[SensorResponse]:
        rows = await self.repository.list_data_types()
        return [SensorResponse.model_validate(row) for row in rows]

    async def get_sensor_data(
        self,
        run_id: str,
        sensors: list[str],
        start: datetime,
        end: datetime,
        gps_offset_on: bool = True,
    ) -> SensorDataResponse:
        """Every reading of `sensors` in `[start, end]`, one series per sensor.

        With `gps_offset_on`, `gps_time_offset_s` is added to the times of lagged
        sensors (see `sensor_catalog`), and the window applies to the shifted times.
        A sensor with no rows in the range (or an unknown run) comes back empty.
        """
        sensors = list(dict.fromkeys(sensors))
        if not sensors:
            raise InvalidParameterError("`sensors` must name at least one sensor")
        if start > end:
            raise InvalidParameterError("`start` must be at or before `end`")

        lagged = self.lagged if gps_offset_on else frozenset()

        series = {name: SensorSeries(time=[], values=[]) for name in sensors}
        rows = await self.repository.list_readings(
            run_id, sensors, start, end, lagged, self.offset
        )
        for row in rows:
            reading = row._mapping
            time = reading["time"]
            if reading["raw_tag"] in lagged:
                time += self.offset
            series[reading["raw_tag"]].time.append(time)
            series[reading["raw_tag"]].values.append(reading["values"])

        return SensorDataResponse(run_id=run_id, start=start, end=end, series=series)

    async def get_lap_sensor_data(
        self,
        run_id: str,
        sensors: list[str],
        lap_ids: list[int],
        start_percent: float,
        end_percent: float,
    ) -> list[LapSensorDataResponse]:
        """For each lap in `lap_ids`, every reading of `sensors` while the lap was
        between `start_percent` and `end_percent`, each with the `lap_percent` of its
        nearest estimated position. One response per lap, in the order given.

        A lap's window is its first and last position in the range. A lap with no
        position in the range comes back with empty series. Raises NotFoundError if
        none of the laps has one (for example, the run hasn't been processed).
        """
        if start_percent > end_percent:
            raise InvalidParameterError(
                "`start_percent` must be at or below `end_percent`"
            )
        rows = await self.lap_progress.list_lap_percents(
            run_id, lap_ids, start_percent, end_percent
        )
        positions_by_lap: dict[int, list[Row[int, datetime, float]]] = {}
        for row in rows:
            positions_by_lap.setdefault(row.lap_id, []).append(row)
        if not any(lap_id in positions_by_lap for lap_id in lap_ids):
            raise NotFoundError("lap_percent", f"{run_id}/{lap_ids}")

        responses = []
        for lap_id in lap_ids:
            positions = positions_by_lap.get(lap_id, [])
            responses.append(
                await self._lap_sensor_data(run_id, sensors, lap_id, positions)
            )
        return responses

    async def _lap_sensor_data(
        self,
        run_id: str,
        sensors: list[str],
        lap_id: int,
        positions: list[Row[int, datetime, float]],
    ) -> LapSensorDataResponse:
        """Every reading of `sensors` from the first to the last of one lap's
        `positions`, each with the `lap_percent` of the nearest one. Empty series
        if there are no positions."""
        if not positions:
            empty = {
                name: LapSensorSeries(time=[], values=[], lap_percent=[])
                for name in dict.fromkeys(sensors)
            }
            return LapSensorDataResponse(
                run_id=run_id, lap_id=lap_id, start=None, end=None, series=empty
            )

        # OrionDB stores naive UTC; Penelope's times are timezone-aware.
        times = [row.time.replace(tzinfo=UTC) for row in positions]
        percents = [row.lap_percent for row in positions]

        data = await self.get_sensor_data(run_id, sensors, times[0], times[-1])
        series = {
            name: LapSensorSeries(
                time=one.time,
                values=one.values,
                lap_percent=nearest_values(one.time, times, percents),
            )
            for name, one in data.series.items()
        }
        return LapSensorDataResponse(
            run_id=run_id, lap_id=lap_id, start=data.start, end=data.end, series=series
        )


def nearest_values(
    times: list[datetime], known_times: list[datetime], values: list[float]
) -> list[float]:
    """For each time, the value at the nearest of `known_times` (ascending, not
    empty), however far away it is."""
    nearest = []
    for time in times:
        i = bisect_left(known_times, time)
        after_last = i == len(known_times)
        if after_last or (i > 0 and time - known_times[i - 1] < known_times[i] - time):
            i -= 1
        nearest.append(values[i])
    return nearest
