from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Location(BaseModel):
    latitude: float
    longitude: float
    altitude: Optional[float] = None
 
class StateCovariance(BaseModel):
    """
    Exact shape isn't decided yet -- whether this ends up position-only or the full CTRA state
    covariance is a decision not made yet. Kept as a generic matrix for now so the field exists on VehicleState without locking in a structure.
 
    TODO: replace `matrix` with named fields (var_lat, var_lon, etc., or the full state-covariance equivalent) once that decision is made.
    """
    matrix: list[list[float]] = Field(default_factory=list)

class VehicleState(BaseModel):
    """
    One fixed-cadence row out of the estimation pipeline. Based on CTRA state defintion, which has 5 params:
        [x, y, v, θ, ω, a] where (x, y) is position, v = speed, theta = heading, w = yaw rate, a = acceleration
    to put into some fancy physics equation
    """
    timestamp: datetime
    speed_mps: float
    heading_deg: Optional[float] = None
    yaw_rate_dps: Optional[float] = None
    accel_mps2: Optional[float] = None
    location: Location
 
    # Estimation metadata: UKF gives a covariance matrix with its estimate to tell you how confident it is about the location...may be useful
    position_covariance: Optional[StateCovariance] = None

    # Set true after smoothing has happened
    is_smoothed: bool = Field(default=False)