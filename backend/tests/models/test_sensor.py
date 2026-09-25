from datetime import datetime

import pandas as pd
import pytest

from backend.models.sensor import SENSOR_STDDEV, cleaned_readings, raw_readings


def test_raw_readings_accepts_scalar_value():
    """Most sensors (voltage, single-axis speed) report one number."""
    df = raw_readings(pd.DataFrame({
        "sensor_id": ["CH_07"],
        "session_id": ["run_2026_09_19_001"],
        "timestamp": [datetime(2026, 9, 19, 12, 0, 0)],
        "value": [12.6],
        "raw_unit": ["V"],
    }))
    assert df["value"].iloc[0] == 12.6
    assert df["sensor_id"].iloc[0] == "CH_07"
    assert df["session_id"].iloc[0] == "run_2026_09_19_001"
    # scalar sensors have no axis
    assert pd.isna(df["axis"].iloc[0])


def test_raw_readings_multi_axis_is_one_row_per_axis():
    """IMU-style sensors report multiple axes at once (accel x/y/z) -- long format keeps value a float column."""
    t = datetime(2026, 9, 19, 12, 0, 0)
    df = raw_readings(pd.DataFrame({
        "sensor_id": ["IMU_1"] * 3,
        "session_id": ["run_2026_09_19_001"] * 3,
        "timestamp": [t] * 3,
        "axis": ["x", "y", "z"],
        "value": [0.1, -0.2, 9.8],
    }))
    assert df["value"].dtype == "float64"
    assert dict(zip(df["axis"], df["value"])) == {"x": 0.1, "y": -0.2, "z": 9.8}
    # raw_unit is optional -- confirms it isn't silently required
    assert df["raw_unit"].isna().all()


def test_raw_readings_rejects_missing_required_column():
    """sensor_id and session_id are required; omitting one must fail loudly."""
    with pytest.raises(ValueError, match="sensor_id"):
        raw_readings(pd.DataFrame({
            "session_id": ["run_2026_09_19_001"],
            "timestamp": [datetime(2026, 9, 19, 12, 0, 0)],
            "value": [1.0],
        }))  # no sensor_id


def test_raw_readings_accepts_arbitrary_unresolved_sensor_id():
    """
    sensor_id is intentionally an untyped string -- an ambiguous/cryptic
    raw label (e.g. a channel number) must still construct successfully.
    Resolving it into a real name is CleanService's job, not this model's.
    """
    df = raw_readings(pd.DataFrame({
        "sensor_id": ["0x142"],
        "session_id": ["run_2026_09_19_001"],
        "timestamp": [datetime(2026, 9, 19, 12, 0, 0)],
        "value": [3.3],
    }))
    assert df["sensor_id"].iloc[0] == "0x142"


def test_raw_readings_normalizes_columns_and_timestamps():
    """Output always has the full schema in order, with timestamps in UTC."""
    df = raw_readings(pd.DataFrame({
        "value": [3.3],
        "timestamp": [datetime(2026, 9, 19, 12, 0, 0)],
        "sensor_id": ["CH_07"],
        "session_id": ["run_2026_09_19_001"],
    }))
    assert list(df.columns) == ["session_id", "sensor_id", "timestamp", "axis", "value", "raw_unit"]
    assert str(df["timestamp"].dt.tz) == "UTC"


def test_cleaned_readings_has_no_per_row_stddev():
    """stddev is a per-sensor mapping (SENSOR_STDDEV), not duplicated onto every reading."""
    df = cleaned_readings(pd.DataFrame({
        "sensor_id": ["CH_07"],
        "session_id": ["run_2026_09_19_001"],
        "name": ["battery_voltage"],
        "timestamp": [datetime(2026, 9, 19, 12, 0, 0)],
        "value": [12.6],
    }))
    assert "stddev" not in df.columns
    assert df["name"].iloc[0] == "battery_voltage"
    assert isinstance(SENSOR_STDDEV, dict)


def test_cleaned_readings_requires_name():
    with pytest.raises(ValueError, match="name"):
        cleaned_readings(pd.DataFrame({
            "sensor_id": ["CH_07"],
            "session_id": ["run_2026_09_19_001"],
            "timestamp": [datetime(2026, 9, 19, 12, 0, 0)],
            "value": [12.6],
        }))
