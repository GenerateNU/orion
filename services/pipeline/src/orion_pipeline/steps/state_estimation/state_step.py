from collections.abc import Iterator

import pandas as pd

from orion_core.queries.orion_queries import select_cleaned_readings
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.state_estimation.ukf_step import SENSORS, Tick, UKFStep
from orion_pipeline.steps.step_registry import register_step


@register_step
class StateStep(PipelineStep):
    """Forward pass: run UKFStep over cleaned sensor data and write its ticks.
    The RTS pass will smooth its output into estimated_car_state.
    DB TABLES: FROM Orion[cleaned_data] -> TO Orion[ukf_states]

    Schema: FROM [time, sensor, values]
    -> TO [run_id, time, origin_lat, origin_lon, x, p, x_pred, p_pred, cross_cov]
    """

    name = "state_step"
    depends_on = ("clean_step",)
    reads_from = "oriondb"
    output_table = "ukf_states"
    pagination_key = ("time", "sensor")

    def prepare(self, ctx: RunContext) -> None:
        super().prepare(ctx)
        self.ukf = UKFStep()

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        return self.reader.iter_pages(
            select_cleaned_readings(ctx.run_id, SENSORS.keys()), self.pagination_key
        )

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """Ticks [time, x, P, x_pred, P_pred, C] -> ukf_states rows, arrays flattened."""
        origin = self.ukf.origin
        if origin is None:
            raise RuntimeError("Origin not set: no GPS fix was seen.")

        def flat(arrays: pd.Series) -> list[list[float] | None]:
            return [None if a is None else a.ravel().tolist() for a in arrays]

        return pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "time": df["time"],
                "origin_lat": origin[0],
                "origin_lon": origin[1],
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
        for page in self.extract(ctx):
            self._write_ticks(self.ukf.push(page), ctx)
        self._write_ticks(self.ukf.flush(), ctx)

    def _write_ticks(self, ticks: list[Tick], ctx: RunContext) -> None:
        if ticks:
            self.write(self.transform(pd.DataFrame(ticks), ctx), ctx)
