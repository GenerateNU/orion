
"""
CleanService -- normalizes raw, ambiguously-labeled sensors and gives them common names.
"""


import pandas as pd


class CleanService:
    def clean(self, raw_readings: pd.DataFrame) -> pd.DataFrame:
        """Normalize units, dedupe, and drop obviously corrupt readings.
        Takes RAW_READING_SCHEMA rows, returns CLEANED_READING_SCHEMA rows."""
        raise NotImplementedError

    def resolve_name(self, sensor_id: str) -> str:
        """Map an ambiguous raw sensor_id to a known semantic channel name."""
        raise NotImplementedError
