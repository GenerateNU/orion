from datetime import datetime

from orion_backend import (
    derived_metrics,  # noqa: F401  (importing registers every metric)
)
from orion_backend.core.exceptions import NotFoundError
from orion_backend.derived_metrics.metric_registry import METRICS
from orion_backend.schemas.derived_metric_schema import DerivedMetricResponse
from orion_backend.schemas.sensor_schema import SensorDataResponse
from orion_backend.services.sensor_service import SensorService


class DerivedMetricService:
    def __init__(self, sensor_service: SensorService):
        self.sensor_service = sensor_service

    def list_metrics(self) -> list[DerivedMetricResponse]:
        return [
            DerivedMetricResponse(name=metric.name, unit=metric.unit)
            for metric in METRICS.values()
        ]

    async def get_metric_data(
        self, run_id: str, name: str, start: datetime, end: datetime
    ) -> SensorDataResponse:
        """The metric computed from its input sensors' readings in `[start, end]`."""
        metric = METRICS.get(name)
        if metric is None:
            raise NotFoundError("Derived metric", name)
        raw = await self.sensor_service.get_sensor_data(
            run_id, list(metric.inputs), start, end
        )
        return SensorDataResponse(
            run_id=run_id, start=start, end=end, series={name: metric.run(raw.series)}
        )
