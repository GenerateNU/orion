"""
StateService -- UKF forward pass + URTS backward smoothing pass (if we chose RTS).
Kept as separate methods because they are structurally two different passes over the data
"""
 
from __future__ import annotations
 
from models.sensor import CleanedReading
from models.vehicle import VehicleState
 
 
class StateService:
    def predict_forward(self, cleaned_readings: list[CleanedReading]) -> list[VehicleState]:
        """Run the UKF forward, one tick at a time (past-and-current-only).
        Output rows have is_smoothed=False."""
        raise NotImplementedError
 
    def smooth(self, forward_states: list[VehicleState]) -> list[VehicleState]:
        """Run the URTS backward pass over a completed forward run.
        Output rows have is_smoothed=True."""
        raise NotImplementedError
 
    def estimate_lap(self, cleaned_readings: list[CleanedReading]) -> list[VehicleState]:
        """Convenience wrapper: predict_forward() then smooth() for one full lap."""
        raise NotImplementedError