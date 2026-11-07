from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


# Unit conversions
class UnitConversions:
    METERS_PER_DEGREE_LAT = 111_320.0
    MPS_PER_MPH = 0.44704
    RADPS_PER_MDPS = np.pi / 180 / 1000


# Hardcoded that we have to figure out based on the lags on gps and speed
GPS_STD_M = 1.5
SPEED_STD_MPS = 0.5
# Yaw rate noise while driving (vibration), measured from recorded runs
GYRO_STD_RADPS = 0.05
# Zero-speed update while parked: how tightly [speed m/s, turn rate rad/s] are
# held at 0
STATIONARY_STD = (0.05, 0.01)


class ImuMount:
    """How the VCU IMU sits in the car, measured from recorded runs.

    The board is tilted ~30 deg, so yaw rate isn't one gyro axis: it's the gyro
    projected onto UP, the gravity direction in the IMU's axes (median
    vcu_imu_accel, the same on every run checked). Turning left (CCW) reads
    positive, matching the state's OMEGA. YAW_BIAS_RADPS is the projected
    reading while parked, also the same on every run.
    """

    UP = np.array([-0.859, -0.037, 0.511])
    YAW_BIAS_RADPS = 0.0075


class PhysicsModelConfig:
    def __init__(
        self,
        model_name: str,
        model_params: dict[str, Any],
        straight_threshold: float = 1e-3,
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


@dataclass(frozen=True)
class SensorConfig:
    """noise_std in the filter's units (m, m/s). Readings whose NIS exceeds the
    gate_confidence chi-square quantile are skipped; None turns gating off."""

    noise_std: float
    gate_confidence: float | None = 0.99


@dataclass(frozen=True)
class UKFConfig:
    """Settings for the UKF. The defaults are the values it used to hardcode.

    tick: grid spacing.
    max_gap: a longer silence restarts the filter instead of extrapolating.
    min_heading_distance_m: the first two GPS fixes must be this far apart.
    max_heading_time: a first fix older than this is replaced by the newest
        one, so slow GPS drift while parked can't add up to a start.
    stationary_speed_mps: a vcu_speed reading below this also holds speed and
        turn rate at 0, so GPS jitter while parked doesn't become motion.
    p0: diagonal of the starting covariance for [px, py, v, theta, omega, a].
        The heading entry is replaced at startup by the uncertainty the two
        fixes actually give: 2 * gps_std^2 / distance^2.
    alpha, beta, kappa: unscented transform parameters.
    physics: model name and params, looked up in ukf_step.PHYSICS_MODELS.
    sensors: sensor name -> noise and gate; UKFStep._measurement must know each name.
    """

    tick: pd.Timedelta = pd.Timedelta("10ms")
    max_gap: pd.Timedelta = pd.Timedelta("1s")
    min_heading_distance_m: float = 10.0
    max_heading_time: pd.Timedelta = pd.Timedelta("5s")
    stationary_speed_mps: float = 0.2
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
            # Ungated: a gated GPS locks the filter out once it drifts, and GPS
            # is the only thing that can pull it back.
            "gps_location": SensorConfig(GPS_STD_M, gate_confidence=None),
            # Ungated too: a gate locked speed out the same way it did GPS
            "vcu_speed": SensorConfig(SPEED_STD_MPS, gate_confidence=None),
            # Ungated like GPS: it's the only direct look at turn rate
            "vcu_imu_gyro": SensorConfig(GYRO_STD_RADPS, gate_confidence=None),
        }
    )
