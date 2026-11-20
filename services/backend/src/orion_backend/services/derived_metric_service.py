import asyncio
from bisect import bisect_left, bisect_right
from datetime import UTC, datetime

from orion_backend import (
    derived_metrics,  # noqa: F401  (importing registers every metric)
)
from orion_backend.core.exceptions import InvalidParameterError, NotFoundError
from orion_backend.derived_metrics.metric_registry import METRICS
from orion_backend.schemas.derived_metric_schema import DerivedMetricResponse
from orion_backend.schemas.sensor_schema import SensorDataResponse, SensorSeries
from orion_backend.services.run_service import RunService
from orion_backend.services.sensor_service import SensorService


class DerivedMetricService:
    def __init__(self, sensor_service: SensorService, run_service: RunService):
        self.sensor_service = sensor_service
        self.run_service = run_service

    def list_metrics(self) -> list[DerivedMetricResponse]:
        return [
            DerivedMetricResponse(name=metric.name, unit=metric.unit)
            for metric in METRICS.values()
        ]

    async def get_metric_data(
        self, run_id: str, name: str, start: datetime, end: datetime
    ) -> SensorDataResponse:
        """The metric computed over the whole run, then cut to `[start, end]`.

        Computing over the run's own bounds (not the window) keeps stateful
        metrics such as running totals identical in every window of the run.
        A run without bounds (no readings yet) comes back as an empty series.
        """
        start, end = _as_utc(start), _as_utc(end)
        if start > end:
            raise InvalidParameterError("`start` must be at or before `end`")
        metric = METRICS.get(name)
        if metric is None:
            raise NotFoundError("Derived metric", name)

        run = await self.run_service.get_run(run_id)
        if run.start_time is None or run.end_time is None:
            series = SensorSeries(time=[], values=[])
        else:
            raw = await self.sensor_service.get_sensor_data(
                run_id, list(metric.inputs), run.start_time, run.end_time
            )
            # pandas work is CPU-bound and synchronous; in a worker thread it
            # doesn't hold up other requests on the event loop.
            computed = await asyncio.to_thread(metric.run, raw.series)
            series = _window(computed, start, end)

        return SensorDataResponse(
            run_id=run_id, start=start, end=end, series={name: series}
        )


def _as_utc(value: datetime) -> datetime:
    """A naive datetime read as UTC, so it compares with the aware readings."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _window(series: SensorSeries, start: datetime, end: datetime) -> SensorSeries:
    """The samples with `start <= time <= end`; `time` is ascending."""
    lo = bisect_left(series.time, start)
    hi = bisect_right(series.time, end)
    return SensorSeries(time=series.time[lo:hi], values=series.values[lo:hi])
