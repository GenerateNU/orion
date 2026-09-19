from datetime import datetime
 
import pytest
from pydantic import ValidationError
 
from backend.models.sensor import CleanedReading, RawSensorReading
 
 
def test_raw_sensor_reading_accepts_scalar_value():
    """Most sensors (voltage, single-axis speed) report one number."""
    reading = RawSensorReading(
        sensor_id="CH_07",
        session_id="run_2026_09_19_001",
        timestamp=datetime(2026, 9, 19, 12, 0, 0),
        value=12.6,
        raw_unit="V",
    )
    assert reading.value == 12.6
    assert reading.sensor_id == "CH_07"
    assert reading.session_id == "run_2026_09_19_001"
 
 
def test_raw_sensor_reading_accepts_multi_axis_value():
    """IMU-style sensors report multiple axes at once (accel x/y/z)."""
    reading = RawSensorReading(
        sensor_id="IMU_1",
        session_id="run_2026_09_19_001",
        timestamp=datetime(2026, 9, 19, 12, 0, 0),
        value={"x": 0.1, "y": -0.2, "z": 9.8},
    )
    assert reading.value == {"x": 0.1, "y": -0.2, "z": 9.8}
    # raw_unit is optional -- confirms it isn't silently required
    assert reading.raw_unit is None
 
 
def test_raw_sensor_reading_rejects_missing_required_field():
    """sensor_id and session_id are required; omitting one must fail loudly."""
    with pytest.raises(ValidationError):
        RawSensorReading(
            session_id="run_2026_09_19_001",
            timestamp=datetime(2026, 9, 19, 12, 0, 0),
            value=1.0,
        )  # no sensor_id
 
 
def test_raw_sensor_reading_accepts_arbitrary_unresolved_sensor_id():
    """
    sensor_id is intentionally an untyped string -- an ambiguous/cryptic
    raw label (e.g. a channel number) must still construct successfully.
    Resolving it into a real name is CleanService's job, not this model's.
    """
    reading = RawSensorReading(
        sensor_id="0x142",
        session_id="run_2026_09_19_001",
        timestamp=datetime(2026, 9, 19, 12, 0, 0),
        value=3.3,
    )
    assert reading.sensor_id == "0x142"
 
 
def test_cleaned_reading_stddev_defaults_to_none():
    """stddev isn't known until CleanService computes/looks it up -- must default to None."""
    cleaned = CleanedReading(
        sensor_id="CH_07",
        session_id="run_2026_09_19_001",
        name="battery_voltage",
        timestamp=datetime(2026, 9, 19, 12, 0, 0),
        value=12.6,
    )
    assert cleaned.stddev is None
    assert cleaned.name == "battery_voltage"