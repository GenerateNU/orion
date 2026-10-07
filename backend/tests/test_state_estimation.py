import pandas as pd
import pytest

from services.state_estimation_service import StateEstimationService


#testing that it takes in a dataframe
def make_valid_input():
    return pd.DataFrame({
        "timestamp": [0.0, 0.01, 0.02],
        "latitude": [42.0, 42.0001, 42.0002],
        "longitude": [-71.0, -71.0001, -71.0002],
        "longitudinal_acceleration": [0.1, 0.2, 0.1],
        "lateral_acceleration": [0.0, 0.1, 0.0],
        "turn_rate": [0.01, 0.02, 0.01],
        "vehicle_speed": [10.0, 10.1, 10.2],
    })

#Does this output properly
def test_valid_input():
    service = StateEstimationService()

    result = service.estimate_position(make_valid_input())

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == [
        "timestamp",
        "latitude",
        "longitude",
    ]

#if there is columns missing how does it handle it 
def test_missing_column():
    service = StateEstimationService()

    df = make_valid_input().drop(columns=["turn_rate"])

    with pytest.raises(ValueError):
        service.estimate_position(df)


#if the timestamps are not in order how does it handle it (because speed/velocity are time dependant. Mismatched times could provide opposite outputs)
def test_unsorted_timestamp():
    service = StateEstimationService()

    df = make_valid_input()
    df["timestamp"] = [0.02, 0.01, 0.00]

    with pytest.raises(ValueError):
        service.estimate_position(df)