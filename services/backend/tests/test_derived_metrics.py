import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

from orion_backend.core.exceptions import NotFoundError
from orion_backend.derived_metrics.base_metric import DerivedMetric
from orion_backend.derived_metrics.metric_registry import METRICS, register_metric
from orion_backend.schemas.derived_metric_schema import DerivedMetricResponse
from orion_backend.schemas.sensor_schema import SensorDataResponse, SensorSeries
from orion_backend.services.derived_metric_service import DerivedMetricService

T0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(seconds=1)
INPUTS = {
    "current": SensorSeries(time=[T0, T1], values=[[2.0], [None]]),
    "voltage": SensorSeries(time=[T0, T1], values=[[0.0, 3.0], [0.0, 4.0]]),
}


@register_metric
class Power(DerivedMetric):
    name = "test/power"
    unit = "W"
    inputs = ("current", "voltage")

    def align(self, inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
        return pd.DataFrame(
            {"current": inputs["current"][0], "voltage": inputs["voltage"][1]}
        )

    def compute(self, aligned: pd.DataFrame) -> pd.Series:
        return aligned["current"] * aligned["voltage"]


def service() -> DerivedMetricService:
    async def get_sensor_data(run_id, sensors, start, end):
        assert sensors == ["current", "voltage"]
        return SensorDataResponse(run_id=run_id, start=start, end=end, series=INPUTS)

    return DerivedMetricService(SimpleNamespace(get_sensor_data=get_sensor_data))  # type: ignore[arg-type]


def test_register_metric_adds_an_instance_by_name():
    assert isinstance(METRICS["test/power"], Power)


def test_run_converts_inputs_and_drops_nan_outputs():
    assert Power().run(INPUTS) == SensorSeries(time=[T0], values=[[6.0]])


def test_list_metrics_returns_each_registered_metric():
    assert (
        DerivedMetricResponse(name="test/power", unit="W") in service().list_metrics()
    )


def test_get_metric_data_returns_the_metric_keyed_by_name():
    response = asyncio.run(service().get_metric_data("run", "test/power", T0, T1))
    assert response.series == {"test/power": SensorSeries(time=[T0], values=[[6.0]])}


def test_get_metric_data_rejects_an_unknown_metric():
    with pytest.raises(NotFoundError):
        asyncio.run(service().get_metric_data("run", "nope", T0, T1))
