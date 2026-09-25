"""
Vehicle states: fixed-cadence rows out of the estimation pipeline. Based on CTRA state defintion, which has 5 params:
    [x, y, v, θ, ω, a] where (x, y) is position, v = speed, theta = heading, w = yaw rate, a = acceleration
to put into some fancy physics equation
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from models.frames import validate_frame

VEHICLE_STATE_SCHEMA = {
    "timestamp": "datetime64[ns, UTC]",
    "speed_mps": "float64",
    "heading_deg": "float64",
    "yaw_rate_dps": "float64",
    "accel_mps2": "float64",
    "latitude": "float64",
    "longitude": "float64",
    "altitude": "float64",  # not every sensor setup reports altitude
}
VEHICLE_STATE_REQUIRED = {"timestamp", "speed_mps", "latitude", "longitude"}


def vehicle_states(df: pd.DataFrame) -> pd.DataFrame:
    return validate_frame(df, VEHICLE_STATE_SCHEMA, VEHICLE_STATE_REQUIRED)


@dataclass
class StateEstimate:
    """
    One run of the estimation pipeline: the state rows plus the UKF's covariance for each row.

    covariance is a numpy array of shape (len(states), n, n), row i is the covariance for states row i.
    UKF gives a covariance matrix with its estimate to tell you how confident it is about the location...may be useful
    TODO: exact n isn't decided yet -- position-only (2x2) or the full CTRA state covariance.
    """
    states: pd.DataFrame
    covariance: np.ndarray | None = None

    # Set true after smoothing has happened. Applies to the whole run, so it lives here instead of on every row.
    is_smoothed: bool = False

    def __post_init__(self):
        self.states = vehicle_states(self.states)
        if self.covariance is not None:
            self.covariance = np.asarray(self.covariance, dtype=np.float64)
            if self.covariance.ndim != 3 or self.covariance.shape[0] != len(self.states) \
                    or self.covariance.shape[1] != self.covariance.shape[2]:
                raise ValueError(
                    f"covariance must have shape ({len(self.states)}, n, n), got {self.covariance.shape}"
                )
