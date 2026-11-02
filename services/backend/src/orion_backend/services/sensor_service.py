from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import InvalidParameterError
from orion_backend.repositories.sensor_repository import SensorRepository
from orion_backend.schemas.sensor_schema import (
    SensorDataResponse,
    SensorResponse,
    SensorSeries,
)
from orion_core.db.sensor_catalog import lagged_raw_tags
from orion_core.settings import get_settings


class SensorService:
    def __init__(self, penelope_db: AsyncSession):
        self.repository = SensorRepository(penelope_db)
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
