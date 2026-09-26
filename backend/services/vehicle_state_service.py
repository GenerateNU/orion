"""
StateService -- UKF forward pass + URTS backward smoothing pass (if we chose RTS).
Kept as separate methods because they are structurally two different passes over the data
"""

import pandas as pd

from models.vehicle import StateEstimate


class StateService:
    def predict_forward(self, cleaned_readings: pd.DataFrame) -> StateEstimate:
        """Run the UKF forward, one tick at a time (past-and-current-only).
        Takes CLEANED_READING_SCHEMA rows; noise for the R matrix comes from SENSOR_STDDEV.
        Output has is_smoothed=False."""
        raise NotImplementedError

    def smooth(self, forward: StateEstimate) -> StateEstimate:
        """Run the URTS backward pass over a completed forward run.
        Output has is_smoothed=True."""
        raise NotImplementedError

    def estimate_lap(self, cleaned_readings: pd.DataFrame) -> StateEstimate:
        """Convenience wrapper: predict_forward() then smooth() for one full lap."""
        raise NotImplementedError
