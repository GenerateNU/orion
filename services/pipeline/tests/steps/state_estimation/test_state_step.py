from datetime import datetime, timedelta
from unittest.mock import Mock

import pandas as pd
import pytest

from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.state_estimation.state_step import StateStep


@pytest.fixture
def state_step(tmp_path):
    """Create a StateStep with a mock reader/writer."""
    reader = Mock()  # not used in transform()
    writer = Mock()  # not used in transform()
    step = StateStep(reader, writer)
    return step


def synthetic_readings(origin_lat=42.3, origin_lon=-71.1, seconds=10, hz=10):
    """Generate synthetic GPS + speed readings: straight line, constant speed.

    Returns DataFrame with columns: time, sensor, values
    """
    times = [datetime.now() + timedelta(seconds=i/hz) for i in range(seconds * hz)]
    rows = []

    # GPS: straight line north at origin
    # Speed: constant 5 m/s
    for i, t in enumerate(times):
        if i % 10 == 0:  # GPS at 1 Hz
            # Move 0.5 m north per second = 0.5 * i / hz meters north
            distance_north = 5.0 * i / hz  # meters
            lat = origin_lat + distance_north / 111_320.0
            lon = origin_lon
            rows.append({"time": t, "sensor": "gps_location", "values": [lat, lon]})

        # Speed at 10 Hz
        rows.append({"time": t, "sensor": "vcu_speed", "values": [5.0]})  # m/s

    return pd.DataFrame(rows)


def test_transform_straight_line(state_step):
    """Transform synthetic straight-line data to lat/lon output."""
    df = synthetic_readings(seconds=5)

    ctx = RunContext(run_id="test-run", penelope_reader=None)
    state_step.prepare(ctx)

    # transform() now handles _filter() internally
    result = state_step.transform(df, ctx)

    # Check output shape and columns
    assert "latitude" in result.columns
    assert "longitude" in result.columns
    assert "time" in result.columns
    assert len(result) > 0

    # Latitudes should increase (moving north)
    lats = result["latitude"].dropna()
    assert len(lats) > 1
    assert lats.iloc[-1] > lats.iloc[0]
