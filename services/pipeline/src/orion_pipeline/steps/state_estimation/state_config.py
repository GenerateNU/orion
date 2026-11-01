"""State estimation configuration."""

import tomllib
from dataclasses import dataclass

import numpy as np


@dataclass
class SensorConfig:
    """One sensor's measurement model."""

    std: list[float]
    gate: float

    @property
    def R(self) -> np.ndarray:
        """Measurement noise covariance matrix."""
        return np.diag(np.array(self.std) ** 2)


@dataclass
class StateConfig:
    """State estimation config loaded from TOML."""

    straight_threshold: float
    sigma_jerk: float
    sigma_alpha: float
    covariance_diag: list[float]
    sensors: dict[str, SensorConfig]

    @property
    def P0(self) -> np.ndarray:
        """Initial state uncertainty matrix."""
        return np.diag(self.covariance_diag)

    @classmethod
    def load(cls, path: str) -> "StateConfig":
        """Load config from TOML file."""
        with open(path, "rb") as f:
            data = tomllib.load(f)

        model = data["model"]
        sensors_raw = data["sensors"]
        sensors = {
            name: SensorConfig(std=cfg["std"], gate=cfg["gate"])
            for name, cfg in sensors_raw.items()
        }

        return cls(
            straight_threshold=model["straight_threshold"],
            sigma_jerk=model["sigma_jerk"],
            sigma_alpha=model["sigma_alpha"],
            covariance_diag=data["initial_state"]["covariance_diag"],
            sensors=sensors,
        )