"""MetricService -- computes derived metrics over completed VehicleState sequences."""
 
from __future__ import annotations

from models.metrics import AnalysisResult
from models.vehicle import VehicleState
 
 
class MetricService:
    def analyze_window(self, states: list[VehicleState]) -> AnalysisResult:
        """Compute metrics over an arbitrary time window of states."""
        raise NotImplementedError
 
    def analyze_lap(self, states: list[VehicleState], lap_number: int) -> AnalysisResult:
        """Compute metrics over one full lap's worth of states."""
        raise NotImplementedError