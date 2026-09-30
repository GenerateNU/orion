"""
Sensor-side models: what comes IN to the pipeline, before we know how it maps onto a VehicleState.

Readings are DataFrames in long format: one row per (sensor, timestamp, axis). Scalar sensors (voltage) leave axis empty;
multi-axis sensors (accel xyz) get one row per axis, so `value` is always a plain float column and stays vectorizable.

sensor_id on raw readings is deliberately an string so that any sensor id will pass
services/clean_service.py job is to resolve these to generic sensor names that we know
"""
import pandas as pd

from models.frames import validate_frame

RAW_READING_SCHEMA = {
    "session_id": "string",
    "sensor_id": "string",
    "timestamp": "datetime64[ns, UTC]",
    "axis": "string",       # None for scalar sensors, "x"/"y"/"z" for multi-axis
    "value": "float64",
    "raw_unit": "string",
}
RAW_READING_REQUIRED = {"session_id", "sensor_id", "timestamp", "value"}

CLEANED_READING_SCHEMA = {
    "session_id": "string",
    "sensor_id": "string",
    "name": "string",       # resolved generic name, e.g. "battery_voltage"
    "timestamp": "datetime64[ns, UTC]",
    "axis": "string",
    "value": "float64",
}
CLEANED_READING_REQUIRED = {"session_id", "sensor_id", "name", "timestamp", "value"}

# measurement noise estimate per generic sensor name; feeds the UKF's R matrix..one of the factors that tells UKF whether to trust the sensor or prediction more
# Lives here instead of on every reading since it's a property of the sensor, not of each data point.
# TODO: fill in from sensor datasheets / calibration runs
SENSOR_STDDEV: dict[str, float] = {}


def raw_readings(df: pd.DataFrame) -> pd.DataFrame:
    """As-received readings, exactly as they arrived from the sensors."""
    return validate_frame(df, RAW_READING_SCHEMA, RAW_READING_REQUIRED)


def cleaned_readings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Raw readings normalized (units, dedup, outliers filtered) and tagged with a resolved generic name once their sensor identity is known.
    """
    return validate_frame(df, CLEANED_READING_SCHEMA, CLEANED_READING_REQUIRED)
