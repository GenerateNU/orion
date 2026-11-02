from collections.abc import Callable, Iterator
from typing import Any

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
from orion_pipeline.steps.state_estimation.state_config import StateConfig
from orion_pipeline.steps.step_registry import register_step

METERS_PER_DEGREE_LAT = 111_320.0


@register_step
class StateStep(PipelineStep):
    """UKF forward + URTS backward smoothing -> estimated_car_state."""

    name = "state_step"
    depends_on = ("clean_step",)
    reads_from = "oriondb"
    output_table = "estimated_car_state"

    def __init__(self, reader: OrionDBClient, writer: OrionDBClient):
        super().__init__(reader, writer)
        self.config = StateConfig.load("services/pipeline/config/state_config.toml")
        self.model = CTRAModel(self.config)
        # self.urts = RauchTiedemannUnscentedKalmanSmoother(self.model)

    def prepare(self, ctx: RunContext) -> None:
        super().prepare(ctx)
        self.ukf: UnscentedKalmanFilter | None = None
        self.tick_time: pd.Timestamp | None = None
        self.origin: tuple[float, float] | None = None
        self.first_fix: tuple[pd.Timestamp, np.ndarray] | None = None
        self.ticks: list[tuple[Any, ...]] = []

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        """Pull all cleaned readings for this run, ordered by time and sensor."""
        yield self.reader.read_all(
            select_cleaned_readings(ctx.run_id, self.config.sensors.keys()),
            ("time", "sensor"),
        )

    def transform(self, readings: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """UKF forward + URTS backward -> estimated_car_state rows."""
        self._filter(readings)

        if self.origin is None:
            raise RuntimeError("Origin not set: no GPS fix was seen.")

        ticks_df = pd.DataFrame(
            self.ticks, columns=["time", "x", "P", "x_pred", "P_pred", "C"]
        )

        # TODO: Run URTS backward pass here
        # x_smooth, P_smooth = self.urts.smooth(...)

        x_estimates = ticks_df["x"]

        lats: list[float | None] = []
        lons: list[float | None] = []
        for x in x_estimates:
            if x is None:
                lats.append(None)
                lons.append(None)
            else:
                lat, lon = self._xy_to_latlon(x[0], x[1])
                lats.append(lat)
                lons.append(lon)

        return pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "time": ticks_df["time"],
                "latitude": lats,
                "longitude": lons,
            }
        )

    def run(self, ctx: RunContext) -> None:
        """Extract, filter, transform, write."""
        self.prepare(ctx)
        for readings in self.extract(ctx):
            result = self.transform(readings, ctx)
            self.write(result, ctx)

    def _to_xy(self, lat: float, lon: float) -> np.ndarray:
        """Latitude/longitude -> [x east, y north] meters from origin."""
        if self.origin is None:
            raise RuntimeError("Origin not set.")
        origin_lat, origin_lon = self.origin
        x = (lon - origin_lon) * METERS_PER_DEGREE_LAT * np.cos(np.radians(origin_lat))
        y = (lat - origin_lat) * METERS_PER_DEGREE_LAT
        return np.array([x, y])

    def _xy_to_latlon(self, x: float, y: float) -> tuple[float, float]:
        """[x east, y north] meters from origin -> latitude/longitude."""
        if self.origin is None:
            raise RuntimeError("Origin not set.")
        origin_lat, origin_lon = self.origin
        lat = origin_lat + y / METERS_PER_DEGREE_LAT
        lon = origin_lon + x / (METERS_PER_DEGREE_LAT * np.cos(np.radians(origin_lat)))
        return lat, lon

    def _get_measurement_func(self, sensor: str) -> Callable[[np.ndarray], np.ndarray]:
        """Get measurement function for sensor."""
        from orion_pipeline.steps.state_estimation.state import PX, PY, V

        if sensor == "gps_location":
            return lambda s: s[:, [PX, PY]]
        elif sensor == "vcu_speed":
            return lambda s: s[:, [V]]
        else:
            raise ValueError(f"Unknown sensor: {sensor}")

    def _measurement(self, sensor: str, values: list[float]) -> np.ndarray:
        """A reading's values -> z in the filter's units."""
        from orion_pipeline.steps.state_estimation.phys_model_config import MPS_PER_MPH

        if sensor == "gps_location":
            lat, lon = values
            return self._to_xy(lat, lon)
        return np.array([values[0] * MPS_PER_MPH])

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

        self.ukf = UnscentedKalmanFilter(self.model, x0, self.config.P0, self.config)
        self.tick_time = tick_time
        self.first_fix = None
        self.ticks.append((tick_time, x0, self.config.P0.copy(), None, None, None))

    def _step(
        self, tick_time: pd.Timestamp, readings: list[tuple[str, list[float]]]
    ) -> None:
        """Predict to tick_time, apply each reading, and record the tick."""
        ukf = self.ukf
        prev = self.tick_time
        if ukf is None or prev is None:
            raise RuntimeError("Filter stepped before it was started.")

        dt = (tick_time - prev).total_seconds()
        x_pred, P_pred, C = ukf.predict(dt)

        for sensor, values in readings:
            sensor_cfg = self.config.sensors[sensor]
            measurement_func = self._get_measurement_func(sensor)
            ukf.update(
                self._measurement(sensor, values),
                measurement_func,
                sensor_cfg.R,
                sensor_cfg.gate,
            )

        self.ticks.append((tick_time, ukf.x.copy(), ukf.P.copy(), x_pred, P_pred, C))
        self.tick_time = tick_time

    def _filter(self, readings: pd.DataFrame) -> None:
        """Run the filter over readings, one tick at a time."""
        for tick_time, tick_readings in readings.groupby(
            readings["time"].dt.floor(pd.Timedelta(milliseconds=self.config.tick_ms))
        ):
            if (
                self.ukf is not None
                and self.tick_time is not None
                and tick_time - self.tick_time
                > pd.Timedelta(seconds=self.config.max_gap_s)
            ):
                self.ukf = None

            if self.ukf is None or self.tick_time is None:
                self._try_start(tick_time, tick_readings)
                continue

            tick_delta = pd.Timedelta(milliseconds=self.config.tick_ms)
            while self.tick_time + tick_delta < tick_time:
                self._step(self.tick_time + tick_delta, [])
            self._step(
                tick_time,
                list(
                    zip(
                        tick_readings["sensor"],
                        tick_readings["values"],
                        strict=True,
                    )
                ),
            )
