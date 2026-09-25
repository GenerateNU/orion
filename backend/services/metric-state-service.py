"""MetricService -- computes derived metrics over completed vehicle state DataFrames."""

import pandas as pd

from backend.models.metrics import AnalysisResult


class MetricService:
    def analyze_window(self, states: pd.DataFrame) -> AnalysisResult:
        """Compute metrics over an arbitrary time window of states (VEHICLE_STATE_SCHEMA rows)."""
        raise NotImplementedError

    def analyze_lap(self, states: pd.DataFrame, lap_number: int) -> AnalysisResult:
        """Compute metrics over one full lap's worth of states."""
        raise NotImplementedError
