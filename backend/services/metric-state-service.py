"""MetricService -- computes derived metrics over completed VehicleState sequences."""
 
from backend.models.metrics import AnalysisResult
from backend.models.vehicle import VehicleState
 
 
class MetricService:
    def analyze_window(self, states: list[VehicleState]) -> AnalysisResult:
        """Compute metrics over an arbitrary time window of states."""
        raise NotImplementedError
 
    def analyze_lap(self, states: list[VehicleState], lap_number: int) -> AnalysisResult:
        """Compute metrics over one full lap's worth of states."""
        raise NotImplementedError