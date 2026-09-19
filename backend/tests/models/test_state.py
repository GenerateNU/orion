from datetime import datetime
 
import pytest
from pydantic import ValidationError
 
from backend.models.vehicle import Location, StateCovariance, VehicleState
 
 
def _minimal_state(**overrides) -> VehicleState:
    """Build a valid VehicleState with only the required fields, unless overridden."""
    defaults = dict(
        timestamp=datetime(2026, 9, 19, 12, 0, 0),
        speed_mps=27.3,
        location=Location(latitude=42.36, longitude=-71.06),
    )
    defaults.update(overrides)
    return VehicleState(**defaults)
 
 
def test_vehicle_state_constructs_with_only_required_fields():
    """timestamp, speed_mps, location are the required set."""
    state = _minimal_state()
    assert state.speed_mps == 27.3
    assert state.location.latitude == 42.36
 
 
def test_vehicle_state_optional_fields_default_correctly():
    """Fields we don't have values for yet (heading, yaw rate, covariance) must default,
    not be silently required -- and is_smoothed must default False (forward-pass output)."""
    state = _minimal_state()
    assert state.heading_deg is None
    assert state.yaw_rate_dps is None
    assert state.position_covariance is None
    assert state.is_smoothed is False
 
 
def test_vehicle_state_missing_required_field_raises():
    """location is required -- omitting it must fail loudly."""
    with pytest.raises(ValidationError):
        VehicleState(
            timestamp=datetime(2026, 9, 19, 12, 0, 0),
            speed_mps=27.3,
        )  # no location
 
 
def test_location_altitude_is_optional():
    """Not every sensor setup reports altitude -- must not be required."""
    loc = Location(latitude=42.36, longitude=-71.06)
    assert loc.altitude is None
 
 
def test_vehicle_state_accepts_state_covariance_and_smoothed_flag():
    """After URTS, a state carries a StateCovariance and is_smoothed=True."""
    smoothed = _minimal_state(
        position_covariance=StateCovariance(matrix=[[0.5, 0.0], [0.0, 0.5]]),
        is_smoothed=True,
    )
    assert smoothed.is_smoothed is True
    assert smoothed.position_covariance.matrix == [[0.5, 0.0], [0.0, 0.5]]