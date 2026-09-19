
"""
CleanService -- normalizes raw, ambiguously-labeled sensors and gives them common names.
"""
 
from __future__ import annotations
 
from models.sensor import CleanedReading, RawSensorReading
 
class CleanService:
    def clean(self, raw_readings: list[RawSensorReading]) -> list[CleanedReading]:
        """Normalize units, dedupe, and drop obviously corrupt readings."""
        raise NotImplementedError
 
    def resolve_name(self, sensor_id: str) -> str:
        """Map an ambiguous raw sensor_id to a known semantic channel name."""
        raise NotImplementedError