from collections.abc import Iterable, Iterator

import numpy as np
import pandas as pd

from orion_core.queries.orion_queries import select_cleaned_readings
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.state_estimation.ctra_model import CTRAModel
from orion_pipeline.steps.state_estimation.kalman_step.kalman_filter import (
    UnscentedKalmanFilter,
)
from orion_pipeline.steps.state_estimation.phys_model_config import (
    METERS_PER_DEGREE_LAT,
    MPS_PER_MPH,
    PhysicsModelConfig,
)
from orion_pipeline.steps.state_estimation.state import PX, PY, V
from orion_pipeline.steps.step_registry import register_step

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


@register_step
class KalmanStep(PipelineStep):
    """Forward pass: run a UKF over cleaned sensor data on a 10ms grid.
    The RTS step smooths its output into estimated_car_state.
    DB TABLES: FROM Orion[cleaned_data] -> TO Orion[ukf_states]

    Schema: FROM [time, sensor, values]
    -> TO [run_id, time, origin_lat, origin_lon, x, p, x_pred, p_pred, cross_cov]
    """

    name = "kalman_step"
    depends_on = ("clean_step",)
    reads_from = "oriondb"
    output_table = "ukf_states"
    pagination_key = ("time", "sensor")

    def __init__(self, reader: OrionDBClient, writer: OrionDBClient):
        super().__init__(reader, writer)
        self.model = CTRAModel(PhysicsModelConfig("ctra", {}))

    def prepare(self, ctx: RunContext) -> None:
        super().prepare(ctx)
        self.ukf: UnscentedKalmanFilter | None = None
        self.tick_time: pd.Timestamp | None = None
        # (lat, lon) of the run's first GPS fix. Local x/y meters are measured from here.
        self.origin: tuple[float, float] | None = None
        # (time, xy) of a GPS fix waiting for a second one to get a heading
        self.first_fix: tuple[pd.Timestamp, np.ndarray] | None = None
        # One (time, x, P, x_pred, P_pred, C) per tick not yet written. The
        # prediction is None on ticks where the filter (re)started.
        self.ticks: list[tuple] = []

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        return self.reader.iter_pages(
            select_cleaned_readings(ctx.run_id, SENSORS.keys()), self.pagination_key
        )

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """Ticks [time, x, P, x_pred, P_pred, C] -> ukf_states rows, arrays flattened."""

        def flat(arrays: pd.Series) -> list[list[float] | None]:
            return [None if a is None else a.ravel().tolist() for a in arrays]

        return pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "time": df["time"],
                "origin_lat": self.origin[0],
                "origin_lon": self.origin[1],
                "x": flat(df["x"]),
                "p": flat(df["P"]),
                "x_pred": flat(df["x_pred"]),
                "p_pred": flat(df["P_pred"]),
                "cross_cov": flat(df["C"]),
            }
        )

    def run(self, ctx: RunContext) -> None:
        """Run the filter over every page, writing each page's ticks as it goes."""
        self.prepare(ctx)

        leftover = None
        for page in self.extract(ctx):
            readings = pd.concat([leftover, page])
            # A page can end mid-tick, so hold the last tick back for the next page
            tick_times = readings["time"].dt.floor(TICK)
            last_tick = tick_times == tick_times.iloc[-1]
            self._filter(readings[~last_tick])
            self._write_ticks(ctx)
            leftover = readings[last_tick]
        if leftover is not None:
            self._filter(leftover)
            self._write_ticks(ctx)

    def _write_ticks(self, ctx: RunContext) -> None:
        """Write the ticks recorded so far and clear them."""
        if not self.ticks:
            return
        ticks = pd.DataFrame(
            self.ticks, columns=["time", "x", "P", "x_pred", "P_pred", "C"]
        )
        self.write(self.transform(ticks, ctx), ctx)
        self.ticks = []

    def _filter(self, readings: pd.DataFrame) -> None:
        """Run the filter over readings, one 10ms tick at a time."""
        for tick_time, tick_readings in readings.groupby(
            readings["time"].dt.floor(TICK)
        ):
            if self.ukf is not None and tick_time - self.tick_time > MAX_GAP:
                self.ukf = None

            if self.ukf is None:
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
        dt = (tick_time - self.tick_time).total_seconds()
        x_pred, P_pred, C = self.ukf.predict(dt)

        for sensor, values in readings:
            h, R, gate = SENSORS[sensor]
            self.ukf.update(self._measurement(sensor, values), h, R, gate)

        self.ticks.append(
            (tick_time, self.ukf.x.copy(), self.ukf.P.copy(), x_pred, P_pred, C)
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
        self.ticks.append((tick_time, x0, P0.copy(), None, None, None))

    def _measurement(self, sensor: str, values: list[float]) -> np.ndarray:
        """A reading's values -> z in the filter's units."""
        if sensor == "gps_location":
            lat, lon = values
            return self._to_xy(lat, lon)
        return np.array([values[0] * MPS_PER_MPH])

    def _to_xy(self, lat: float, lon: float) -> np.ndarray:
        """Latitude/longitude -> [x east, y north] meters from the origin. Fine at track scale."""
        origin_lat, origin_lon = self.origin
        x = (lon - origin_lon) * METERS_PER_DEGREE_LAT * np.cos(np.radians(origin_lat))
        y = (lat - origin_lat) * METERS_PER_DEGREE_LAT
        return np.array([x, y])
