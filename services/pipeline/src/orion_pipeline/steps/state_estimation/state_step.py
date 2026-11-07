from collections.abc import Iterator

import pandas as pd

from orion_core.queries.orion_queries import select_cleaned_readings
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.state_estimation.ukf_step import UKFStep
from orion_pipeline.steps.state_estimation.urts_smoother import URTS
from orion_pipeline.steps.step_registry import register_step


@register_step
class StateStep(PipelineStep):
    """Forward pass: run UKFStep over cleaned sensor data and write its ticks.
    DB TABLES: FROM Orion[cleaned_data] -> TO Orion[ukf_states]

    Schema: FROM [time, sensor, values]
    -> TO [run_id, time, origin_lat, origin_lon, x, p, x_pred, p_pred, cross_cov]
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
        """Forward pass -> ukf_states rows, with the arrays flattened to lists."""
        arrays = df[["x", "p", "x_pred", "p_pred", "cross_cov"]]
        flat = arrays.map(lambda a: a.ravel().tolist(), na_action="ignore")
        return df.assign(run_id=ctx.run_id, **flat)

    def run(self, ctx: RunContext) -> None:
        """UKF forward pass, then URTS smoothing. Writes the forward pass to
        ukf_states and keeps the smoothed rows on self.smoothed.
        TODO: persist the smoothed rows once their table/columns exist."""
        self.prepare(ctx)
        frame = self._forward_pass(ctx)
        if not frame.empty:
            self.smoothed = URTS.smooth_frame(frame)
            self.write(self.transform(frame, ctx), ctx)
