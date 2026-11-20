import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

from orion_backend.core.exceptions import InvalidParameterError, NotFoundError
from orion_backend.derived_metrics.base_metric import DerivedMetric
from orion_backend.derived_metrics.metric_registry import METRICS, register_metric
from orion_backend.schemas.derived_metric_schema import DerivedMetricResponse
from orion_backend.schemas.sensor_schema import SensorDataResponse, SensorSeries
from orion_backend.services.derived_metric_service import DerivedMetricService

CURRENT = "DTI/Power/DC_Current"
VOLTAGE = "DTI/Power/Input_Voltage"
T0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
T1, T2, T3 = (T0 + timedelta(seconds=s) for s in (1, 2, 3))
INPUTS = {
    CURRENT: SensorSeries(time=[T0, T1], values=[[2.0], [None]]),
    VOLTAGE: SensorSeries(time=[T0, T1], values=[[3.0], [4.0]]),
}
# A whole run, T0..T3, for the service tests.
RUN_INPUTS = {
    CURRENT: SensorSeries(time=[T0, T1, T2, T3], values=[[1.0], [2.0], [3.0], [4.0]]),
    VOLTAGE: SensorSeries(time=[T0, T1, T2, T3], values=[[1.0], [1.0], [1.0], [1.0]]),
}


class Power(DerivedMetric):
    name = "test/power"
    unit = "W"
    inputs = (CURRENT, VOLTAGE)

    def compute(self, aligned: pd.DataFrame) -> pd.Series:
        return aligned[(CURRENT, 0)] * aligned[(VOLTAGE, 0)]


class RunningTotal(DerivedMetric):
    """Stateful: its value at a time depends on everything before it."""

    name = "test/running_total"
    unit = "A"
    inputs = (CURRENT, VOLTAGE)

    def compute(self, aligned: pd.DataFrame) -> pd.Series:
        return aligned[(CURRENT, 0)].cumsum()


@pytest.fixture(autouse=True)
def metrics() -> None:
    register_metric(Power)
    register_metric(RunningTotal)


def service(
    start_time: datetime | None = T0,
    end_time: datetime | None = T3,
    fetches: list[tuple[datetime, datetime]] | None = None,
) -> DerivedMetricService:
    """A service over a fake run `run` with the given bounds. Sensor fetches are
    appended to `fetches` as (start, end)."""

    async def get_sensor_data(run_id, sensors, start, end):
        assert sensors == [CURRENT, VOLTAGE]
        if fetches is not None:
            fetches.append((start, end))
        return SensorDataResponse(
            run_id=run_id, start=start, end=end, series=RUN_INPUTS
        )

    async def get_run(run_id):
        if run_id != "run":
            raise NotFoundError("Run", run_id)
        return SimpleNamespace(start_time=start_time, end_time=end_time)

    return DerivedMetricService(
        SimpleNamespace(get_sensor_data=get_sensor_data),  # type: ignore[arg-type]
        SimpleNamespace(get_run=get_run),  # type: ignore[arg-type]
    )


def get(name: str, start: datetime, end: datetime, svc=None, run_id: str = "run"):
    return asyncio.run((svc or service()).get_metric_data(run_id, name, start, end))


def test_register_metric_adds_an_instance_by_name():
    assert isinstance(METRICS["test/power"], Power)


def test_run_converts_inputs_and_drops_nan_outputs():
    # Current has no value at T1, so the product there is NaN and dropped.
    assert Power().run(INPUTS) == SensorSeries(time=[T0], values=[[6.0]])


def test_list_metrics_returns_each_registered_metric():
    assert (
        DerivedMetricResponse(name="test/power", unit="W") in service().list_metrics()
    )


def test_get_metric_data_returns_the_metric_keyed_by_name():
    response = get("test/power", T0, T3)
    assert response.series == {
        "test/power": SensorSeries(
            time=[T0, T1, T2, T3], values=[[1.0], [2.0], [3.0], [4.0]]
        )
    }


def test_inputs_are_fetched_for_the_whole_run_not_the_window():
    fetches: list[tuple[datetime, datetime]] = []
    get("test/power", T1, T2, service(fetches=fetches))
    assert fetches == [(T0, T3)]


def test_result_is_cut_to_the_window_inclusive():
    response = get("test/power", T1, T2)
    assert response.series["test/power"] == SensorSeries(
        time=[T1, T2], values=[[2.0], [3.0]]
    )
    assert (response.start, response.end) == (T1, T2)


def test_a_window_shows_the_same_values_as_the_whole_run():
    # The running total at T2 counts T0 and T1 too: 1 + 2 + 3, not 3.
    whole = get("test/running_total", T0, T3).series["test/running_total"]
    window = get("test/running_total", T2, T3).series["test/running_total"]
    assert whole.values == [[1.0], [3.0], [6.0], [10.0]]
    assert window == SensorSeries(time=[T2, T3], values=[[6.0], [10.0]])


def test_a_naive_window_is_read_as_utc():
    naive = (T1.replace(tzinfo=None), T2.replace(tzinfo=None))
    assert get("test/power", *naive).series["test/power"].time == [T1, T2]


def test_a_window_outside_the_run_is_empty():
    late = T3 + timedelta(seconds=10)
    assert get("test/power", late, late).series["test/power"] == SensorSeries(
        time=[], values=[]
    )


@pytest.mark.parametrize(("start_time", "end_time"), [(None, None), (T0, None)])
def test_a_run_without_bounds_is_empty_and_reads_no_sensors(start_time, end_time):
    fetches: list[tuple[datetime, datetime]] = []
    svc = service(start_time, end_time, fetches)
    response = get("test/power", T0, T3, svc)
    assert response.series["test/power"] == SensorSeries(time=[], values=[])
    assert fetches == []


def test_get_metric_data_rejects_an_unknown_metric():
    with pytest.raises(NotFoundError):
        get("nope", T0, T1)


def test_get_metric_data_rejects_an_unknown_run():
    with pytest.raises(NotFoundError):
        get("test/power", T0, T1, run_id="nope")


def test_get_metric_data_rejects_a_reversed_window():
    with pytest.raises(InvalidParameterError):
        get("test/power", T2, T1)
