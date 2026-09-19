"""
Sensor-side models: what comes IN to the pipeline, before we know how it maps onto a VehicleState.
 
sensor_id on RawSensorReading is deliberately an string so that any sensor id will pass
services/clean_service.py job is to resolve these to generic sensor names that we know
"""
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel
 
SensorValue = Union[float, dict[str, float]]  # scalar (voltage) or multi-axis (accel xyz)
 

class RawSensorReading(BaseModel):
    """One as-received reading, exactly as it arrived from a sensor."""
    session_id: str
    sensor_id: str
    timestamp: datetime
    value: SensorValue
    raw_unit: Optional[str] = None
 
 
class CleanedReading(BaseModel):
    """
    A RawSensorReading normalized (units, dedup, outliers filtered) and tagged with a resolved generic name once its sensor identity is known.
    """
    session_id: str
    sensor_id: str
    name: str  
    timestamp: datetime
    value: SensorValue
    # measurement noise estimate; feeds the UKF's R matrix..one of the factors that tells UKF whether to trust the sensor or prediction more
    stddev: Optional[float] = None  