from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from orion_pipeline.steps.state_estimation.ctra_model import CTRAModel
from orion_pipeline.steps.state_estimation.kalman_filter import UnscentedKalmanFilter
from orion_pipeline.steps.state_estimation.phys_model_config import (
    PhysicsModelConfig,
    UnitConversions,
)
from orion_pipeline.steps.state_estimation.state import PX, PY, V

TICK = pd.Timedelta("10ms")
# A gap longer than this restarts the filter instead of extrapolating through it
MAX_GAP = pd.Timedelta("1s")
# The first two GPS fixes must be this far apart to give a starting heading
MIN_HEADING_DISTANCE_M = 2.0

# TODO: Revise placeholder values
GPS_STD_M = 1.5
SPEED_STD_MPS = 0.5

# sensor -> (h, R, NIS gate at 99%)
SENSORS = {
    "gps_location": (
        lambda s: s[:, [PX, PY]],
        np.diag([GPS_STD_M**2, GPS_STD_M**2]),
        9.21,
    ),
    "vcu_speed": (
        lambda s: s[:, [V]],
        np.array([[SPEED_STD_MPS**2]]),
        6.63,
    ),
}

# Starting uncertainty for [px, py, v, theta, omega, a]
P0 = np.diag([GPS_STD_M**2, GPS_STD_M**2, 1.0**2, 0.3**2, 0.5**2, 2.0**2])


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

    def __init__(self) -> None:
        self.model = CTRAModel(PhysicsModelConfig("ctra", {}))
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
        tick_times = readings["time"].dt.floor(TICK)
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
            readings["time"].dt.floor(TICK)
        ):
            if (
                self.ukf is not None
                and self.tick_time is not None
                and tick_time - self.tick_time > MAX_GAP
            ):
                self.ukf = None

            if self.ukf is None or self.tick_time is None:
                self._try_start(tick_time, tick_readings)
                continue

            # Ticks with no readings still predict, so the grid stays even
            while self.tick_time + TICK < tick_time:
                self._step(self.tick_time + TICK, [])
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
            h, R, gate = SENSORS[sensor]
            ukf.update(self._measurement(sensor, values), h, R, gate)

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
        if distance < MIN_HEADING_DISTANCE_M:
            return

        speed = distance / (tick_time - first_time).total_seconds()
        x0 = np.array([xy[0], xy[1], speed, np.arctan2(dy, dx), 0.0, 0.0])

        self.ukf = UnscentedKalmanFilter(self.model, x0, P0)
        self.tick_time = tick_time
        self.first_fix = None
        self.ticks.append(Tick(tick_time, x0, P0.copy(), None, None, None))

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
