import pandas as pd
import pytest
import torch

from services import state_estimation_service
from services.state_estimation_service import StateEstimationService


# Long-format readings (one value per row), 10 ms apart -- the shape _estimate_position takes
def make_valid_input(ticks=3, start="2026-10-12 12:00:00"):
    return pd.DataFrame({
        "timestamp": pd.date_range(start, periods=ticks, freq="10ms", tz="UTC"),
        "name": "vcu_speed",
        "value": 10.0,
    })


# Does this output properly
def test_valid_input():
    service = StateEstimationService(None)

    positions, _ = service._estimate_position(make_valid_input())

    assert isinstance(positions, pd.DataFrame)
    assert list(positions.columns) == ["timestamp", "latitude", "longitude"]
    assert len(positions) == 3  # one row per tick


# The last point holds everything the next page needs to continue
def test_returns_last_point():
    service = StateEstimationService(None)
    readings = make_valid_input()

    _, last_point = service._estimate_position(readings)

    assert last_point["time"] == readings["timestamp"].iloc[-1]
    assert last_point["state"].shape == (6,)
    assert last_point["covariance"].shape == (6, 6)
    assert last_point["origin"] == StateEstimationService.PLACEHOLDER_ORIGIN


# Splitting one run into two pages should end in the same place as running it in one go
def test_continuing_from_previous_point_matches_one_page():
    service = StateEstimationService(None)
    readings = make_valid_input(ticks=6)

    _, one_page = service._estimate_position(readings)

    _, first_page = service._estimate_position(readings.iloc[:3])
    _, second_page = service._estimate_position(readings.iloc[3:], first_page)

    assert second_page["time"] == one_page["time"]
    torch.testing.assert_close(second_page["state"], one_page["state"])
    torch.testing.assert_close(second_page["covariance"], one_page["covariance"])


# If there is columns missing how does it handle it
def test_missing_column():
    service = StateEstimationService(None)

    df = make_valid_input().drop(columns=["value"])

    with pytest.raises(ValueError):
        service._estimate_position(df)


# If the timestamps are not in order how does it handle it (because speed/velocity are time dependant)
def test_unsorted_timestamp():
    service = StateEstimationService(None)

    df = make_valid_input().iloc[::-1]

    with pytest.raises(ValueError):
        service._estimate_position(df)


def test_empty_input():
    service = StateEstimationService(None)

    with pytest.raises(ValueError):
        service._estimate_position(make_valid_input().iloc[0:0])


# A page with no data returns no rows and passes every run's last point through to the next page
def test_estimate_state_empty_window_keeps_previous_points(monkeypatch):
    class FakeRepository:
        engine = None

    monkeypatch.setattr(state_estimation_service.pd, "read_sql", lambda query, engine: pd.DataFrame())
    previous_points = {"run-a": {"time": pd.Timestamp("2026-10-12", tz="UTC")}}

    estimated, last_points = StateEstimationService(FakeRepository()).estimate_state(
        pd.Timestamp("2026-10-12 12:00", tz="UTC"),
        pd.Timestamp("2026-10-12 12:01", tz="UTC"),
        previous_points,
    )

    assert estimated.empty
    assert list(estimated.columns) == StateEstimationService.STATE_TABLE_COLUMNS
    assert last_points == previous_points
