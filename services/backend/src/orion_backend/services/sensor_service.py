from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import InvalidParameterError
from orion_backend.repositories.sensor_repository import SensorRepository
from orion_backend.schemas.sensor_schema import (
    SensorDataResponse,
    SensorResponse,
    SensorSeries,
)


class SensorService:
    def __init__(self, penelope_db: AsyncSession):
        self.repository = SensorRepository(penelope_db)

    async def list_sensors(self) -> list[SensorResponse]:
        rows = await self.repository.list_data_types()
        return [SensorResponse.model_validate(row) for row in rows]

    async def get_sensor_data(
        self, run_id: str, sensors: list[str], start: datetime, end: datetime
    ) -> SensorDataResponse:
        """Every reading of `sensors` in `[start, end]`, one series per sensor.

        A sensor with no rows in the range (or an unknown run) comes back empty.
        """
        sensors = list(dict.fromkeys(sensors))
        if not sensors:
            raise InvalidParameterError("`sensors` must name at least one sensor")
        if start > end:
            raise InvalidParameterError("`start` must be at or before `end`")

        series = {name: SensorSeries(time=[], values=[]) for name in sensors}
        for row in await self.repository.list_readings(run_id, sensors, start, end):
            reading = row._mapping
            series[reading["raw_tag"]].time.append(reading["time"])
            series[reading["raw_tag"]].values.append(reading["values"])

        return SensorDataResponse(run_id=run_id, start=start, end=end, series=series)
