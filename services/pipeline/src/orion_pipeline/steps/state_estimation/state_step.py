from collections.abc import Iterator

import numpy as np
import pandas as pd

from orion_core.queries.orion_queries import select_cleaned_readings
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.state_estimation.state import PX, PY
from orion_pipeline.steps.state_estimation.state_model_config import UnitConversions
from orion_pipeline.steps.state_estimation.ukf_step import UKFStep
from orion_pipeline.steps.state_estimation.urts_smoother import URTS
from orion_pipeline.steps.step_registry import register_step


@register_step
class StateStep(PipelineStep):
    """Run UKFStep over cleaned sensor data, smooth it with URTS, and write the
    smoothed positions.
    DB TABLES: FROM Orion[cleaned_data] -> TO Orion[estimated_car_state]

    Schema: FROM [time, sensor, values]
    -> TO [run_id, time, lattitude, longitude]
    """

    name = "state_step"
    depends_on = ("clean_step",)
    reads_from = "oriondb"
    output_table = "estimated_car_state"

    def _forward_pass(self, ctx: RunContext) -> pd.DataFrame:
        """Run the UKF over the run's cleaned readings, read in one go. Returns
        its output as a frame with the run's origin."""
        ukf = UKFStep()
        query = select_cleaned_readings(ctx.run_id, ukf.sensors.keys())
        readings = self.reader.read_frame(
            query.order_by(None).order_by("time", "sensor")
        )

        rows = ukf.push(readings) + ukf.flush()
        if not rows:
            return pd.DataFrame()
        assert ukf.origin is not None  # set by the first GPS fix
        lat, lon = ukf.origin
        return pd.DataFrame(rows).assign(origin_lat=lat, origin_lon=lon)

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        """The forward pass, as one page."""
        frame = self._forward_pass(ctx)
        if not frame.empty:
            yield frame

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """Forward pass -> estimated_car_state rows: URTS-smoothed states, their
        east/north meters converted back to lat/lon around the run's origin.

        Smoothing needs the whole run, which is fine: extract yields it as one page.
        """
        smoothed = URTS.smooth_frame(df)
        east = smoothed["x_smooth"].map(lambda x: x[PX]).to_numpy()
        north = smoothed["x_smooth"].map(lambda x: x[PY]).to_numpy()
        origin_lat = df["origin_lat"].to_numpy()
        meters_per_degree = UnitConversions.METERS_PER_DEGREE_LAT
        return pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "time": smoothed["time"],
                "lattitude": origin_lat + north / meters_per_degree,
                "longitude": df["origin_lon"].to_numpy()
                + east / (meters_per_degree * np.cos(np.radians(origin_lat))),
            }
        )
