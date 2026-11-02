from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

# Unit conversions
class UnitConversions:
    METERS_PER_DEGREE_LAT = 111_320.0
    MPS_PER_MPH = 0.44704

    #lag that we need to edit
    GPS_STD_M = 1.5
    SPEED_STD_MPS = 0.5 


class PhysicsModelConfig:
    def __init__(
        self,
        model_name: str,
        model_params: dict[str, Any],
        straight_threshold: float = 1e-6,
    ) -> None:
        self.model_name = model_name
        self.model_params = model_params
        # rad/s, below this |turn rate| the car is treated as driving straight
        self.straight_threshold = straight_threshold

    def __repr__(self) -> str:
        return (
            f"PhysicsModelConfig(model_name={self.model_name}, "
            f"model_params={self.model_params})"
        )

class SensorConfig:
    """noise_std in the filter's units (m, m/s). Readings whose NIS exceeds the
    gate_confidence chi-square quantile are skipped; None turns gating off."""

    noise_std: float
    gate_confidence: float | None = 0.99


class UKFConfig:
    """Settings for the UKF. The defaults are the values it used to hardcode.

    tick: grid spacing.
    max_gap: a longer silence restarts the filter instead of extrapolating.
    min_heading_distance_m: the first two GPS fixes must be this far apart.
    p0: diagonal of the starting covariance for [px, py, v, theta, omega, a].
    alpha, beta, kappa: unscented transform parameters.
    physics: model name and params, looked up in PHYSICS_MODELS.
    sensors: sensor name -> noise and gate; names must be in SENSOR_KINDS.
    """

    tick: pd.Timedelta = pd.Timedelta("10ms")
    max_gap: pd.Timedelta = pd.Timedelta("1s")
    min_heading_distance_m: float = 2.0
    p0: tuple[float, ...] = (
        GPS_STD_M**2,
        GPS_STD_M**2,
        1.0**2,
        0.3**2,
        0.5**2,
        2.0**2,
    )
    alpha: float = 0.5
    beta: float = 2.0
    kappa: float = 0.0
    physics: PhysicsModelConfig = field(
        default_factory=lambda: PhysicsModelConfig("ctra", {})
    )
    sensors: Mapping[str, SensorConfig] = field(
        default_factory=lambda: {
            "gps_location": SensorConfig(GPS_STD_M),
            "vcu_speed": SensorConfig(SPEED_STD_MPS),
        }
    )