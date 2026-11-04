from datetime import UTC, datetime, timedelta

import pandas as pd

from orion_backend.derived_metrics.base_metric import DerivedMetric
from orion_backend.derived_metrics.metric_registry import METRICS, register_metric
from orion_backend.schemas.sensor_schema import SensorSeries

T0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(seconds=1)


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


def test_register_metric_adds_an_instance_by_name():
    assert isinstance(METRICS["test/power"], Power)


def test_run_converts_inputs_and_drops_nan_outputs():
    result = Power().run(
        {
            "current": SensorSeries(time=[T0, T1], values=[[2.0], [None]]),
            "voltage": SensorSeries(time=[T0, T1], values=[[0.0, 3.0], [0.0, 4.0]]),
        }
    )
    assert result == SensorSeries(time=[T0], values=[[6.0]])
