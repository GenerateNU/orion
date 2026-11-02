import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from statistics import NormalDist
from typing import NamedTuple

import numpy as np
import pandas as pd

from orion_pipeline.steps.state_estimation.ctra_model import CTRAModel
from orion_pipeline.steps.state_estimation.kalman_filter import UnscentedKalmanFilter
from orion_pipeline.steps.state_estimation.physics_model import PhysicsModel
from orion_pipeline.steps.state_estimation.state import PX, PY, V
from orion_pipeline.steps.state_estimation.state_model_config import (
    PhysicsModelConfig,
    UKFConfig,
    UnitConversions,
)

PHYSICS_MODELS: dict[str, Callable[[PhysicsModelConfig], PhysicsModel]] = {
    "ctra": CTRAModel,
}


class SensorKind(NamedTuple):
    dim: int
    h: Callable[[np.ndarray], np.ndarray]
    to_z: Callable[[Sequence[float], Callable[[float, float], np.ndarray]], np.ndarray]


SENSOR_KINDS: dict[str, SensorKind] = {
    "gps_location": SensorKind(
        2, lambda s: s[:, [PX, PY]], lambda values, to_xy: to_xy(values[0], values[1])
    ),
    "vcu_speed": SensorKind(
        1,
        lambda s: s[:, [V]],
        lambda values, to_xy: np.array([values[0] * UnitConversions.MPS_PER_MPH]),
    ),
}


def gate_threshold(confidence: float, dof: int) -> float:
    if dof == 1:
        return NormalDist().inv_cdf((1 + confidence) / 2) ** 2
    if dof == 2:
        return -2.0 * math.log1p(-confidence)
    from scipy.stats import chi2

    return float(chi2.ppf(confidence, dof))


@dataclass(frozen=True)
class Tick:
    """The filter's state at one tick. x_pred, P_pred and C are None on a startup tick."""

    time: pd.Timestamp
    x: np.ndarray
    P: np.ndarray
    x_pred: np.ndarray | None
    P_pred: np.ndarray | None
    C: np.ndarray | None


class UKFStep:
    """Forward UKF pass over time-ordered [time, sensor, values] readings on a 10ms grid.

    Not a pipeline step: no DB, runner or step base class, so it can be used and
    tested on its own. Feed readings in any batch size with push(), then call
    flush() once at the end.
    """

    def __init__(self, config: UKFConfig | None = None) -> None:
        self.config = config or UKFConfig()
        cfg = self.config
        self.model = PHYSICS_MODELS[cfg.physics.model_name](cfg.physics)
        self.p0 = np.diag(cfg.p0)
        # sensor -> (kind, R, NIS gate)
        self.sensors: dict[str, tuple[SensorKind, np.ndarray, float | None]] = {}
        for name, s in cfg.sensors.items():
            kind = SENSOR_KINDS[name]
            gate = (
                None
                if s.gate_confidence is None
                else gate_threshold(s.gate_confidence, kind.dim)
            )
            R = np.diag(np.full(kind.dim, s.noise_std**2))
            self.sensors[name] = (kind, R, gate)

        self.ukf: UnscentedKalmanFilter | None = None
        self.tick_time: pd.Timestamp | None = None
        self.origin: tuple[float, float] | None = None
        self.first_fix: tuple[pd.Timestamp, np.ndarray] | None = None
        self.held: pd.DataFrame | None = None
        self.ticks: list[Tick] = []

    def push(self, readings: pd.DataFrame) -> list[Tick]:
        """Run the filter over readings and return the finished ticks. The last
        tick's readings are held back, since the next batch may add to them."""
        readings = pd.concat([self.held, readings])
        if readings.empty:
            return []
        tick_times = readings["time"].dt.floor(self.config.tick)
        last_tick = tick_times == tick_times.iloc[-1]
        self._filter(readings[~last_tick])
        self.held = readings[last_tick]
        return self._take_ticks()

    def flush(self) -> list[Tick]:
        """Run the held-back readings and return the remaining ticks."""
        if self.held is not None:
            self._filter(self.held)
            self.held = None
        return self._take_ticks()

    def _take_ticks(self) -> list[Tick]:
        ticks, self.ticks = self.ticks, []
        return ticks

    def _filter(self, readings: pd.DataFrame) -> None:
        """Run the filter over readings, one 10ms tick at a time."""

        for tick_time, tick_readings in readings.groupby(
            readings["time"].dt.floor(self.config.tick)
        ):
            if (
                self.ukf is not None
                and self.tick_time is not None
                and tick_time - self.tick_time > self.config.max_gap
            ):
                self.ukf = None

            if self.ukf is None or self.tick_time is None:
                self._try_start(tick_time, tick_readings)
                continue

            # Ticks with no readings still predict, so the grid stays even
            while self.tick_time + self.config.tick < tick_time:
                self._step(self.tick_time + self.config.tick, [])
            self._step(
                tick_time,
                zip(tick_readings["sensor"], tick_readings["values"], strict=True),
            )

    def _step(
        self, tick_time: pd.Timestamp, readings: Iterable[tuple[str, list[float]]]
    ) -> None:
        """Predict to tick_time, apply each reading, and record the tick."""
        ukf = self.ukf
        prev = self.tick_time
        if ukf is None or prev is None:
            raise RuntimeError("Filter stepped before it was started.")

        dt = (tick_time - prev).total_seconds()
        x_pred, P_pred, C = ukf.predict(dt)

        for sensor, values in readings:
            kind, R, gate = self.sensors[sensor]
            ukf.update(kind.to_z(values, self._to_xy), kind.h, R, gate)

        self.ticks.append(
            Tick(tick_time, ukf.x.copy(), ukf.P.copy(), x_pred, P_pred, C)
        )
        self.tick_time = tick_time

    def _try_start(self, tick_time: pd.Timestamp, readings: pd.DataFrame) -> None:
        """Start the filter once two GPS fixes are far enough apart to give a heading."""
        gps = readings.loc[readings["sensor"] == "gps_location", "values"]
        if gps.empty:
            return

        lat, lon = gps.iloc[-1]
        if self.origin is None:
            self.origin = (lat, lon)
        xy = self._to_xy(lat, lon)

        if self.first_fix is None:
            self.first_fix = (tick_time, xy)
            return

        first_time, first_xy = self.first_fix
        dx, dy = xy - first_xy
        distance = np.hypot(dx, dy)
        if distance < self.config.min_heading_distance_m:
            return

        speed = distance / (tick_time - first_time).total_seconds()
        x0 = np.array([xy[0], xy[1], speed, np.arctan2(dy, dx), 0.0, 0.0])

        self.ukf = UnscentedKalmanFilter(self.model, x0, self.p0)
        self.tick_time = tick_time
        self.first_fix = None
        self.ticks.append(Tick(tick_time, x0, self.p0.copy(), None, None, None))

    def _measurement(self, sensor: str, values: list[float]) -> np.ndarray:
        """A reading's values -> z in the filter's units."""
        if sensor == "gps_location":
            lat, lon = values
            return self._to_xy(lat, lon)
        return np.array([values[0] * UnitConversions.MPS_PER_MPH])

    def _to_xy(self, lat: float, lon: float) -> np.ndarray:
        """Latitude/longitude -> [x east, y north] meters from the origin. Fine at track scale."""
        if self.origin is None:
            raise RuntimeError("Origin not set.")
        origin_lat, origin_lon = self.origin
        x = (
            (lon - origin_lon)
            * UnitConversions.METERS_PER_DEGREE_LAT
            * np.cos(np.radians(origin_lat))
        )
        y = (lat - origin_lat) * UnitConversions.METERS_PER_DEGREE_LAT
        return np.array([x, y])
