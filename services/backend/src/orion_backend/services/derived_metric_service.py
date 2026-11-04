from orion_backend import (
    derived_metrics,  # noqa: F401  (importing registers every metric)
)
from orion_backend.derived_metrics.metric_registry import METRICS
from orion_backend.schemas.derived_metric_schema import DerivedMetricResponse


class DerivedMetricService:
    def list_metrics(self) -> list[DerivedMetricResponse]:
        return [
            DerivedMetricResponse(name=metric.name, unit=metric.unit)
            for metric in METRICS.values()
        ]
