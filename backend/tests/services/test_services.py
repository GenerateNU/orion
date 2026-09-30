"""
The services are still stubs -- these pin down their interfaces until the real implementations land.
Replace each test with real behavior tests as the methods get implemented.
"""
import pandas as pd
import pytest

from services.metric_state_service import MetricService
from services.sensor_clean_service import CleanService
from services.vehicle_state_service import StateService

EMPTY = pd.DataFrame()


@pytest.mark.parametrize("call", [
    lambda: MetricService().analyze_window(EMPTY),
    lambda: MetricService().analyze_lap(EMPTY, lap_number=1),
    lambda: CleanService().clean(EMPTY),
    lambda: CleanService().resolve_name("CH_07"),
    lambda: StateService().predict_forward(EMPTY),
    lambda: StateService().smooth(None),
    lambda: StateService().estimate_lap(EMPTY),
])
def test_service_stubs_not_implemented_yet(call):
    with pytest.raises(NotImplementedError):
        call()
