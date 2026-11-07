from collections.abc import Iterator

import pandas as pd

from orion_core.queries.orion_queries import select_cleaned_readings
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.state_estimation.ukf_step import Tick, UKFStep
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
    output_table = "ukf_states"
    pagination_key = ("time", "sensor")

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        """Run the UKF over the cleaned readings page by page, yielding its ticks
        with the run's origin."""
        ukf = UKFStep()
        query = select_cleaned_readings(ctx.run_id, ukf.sensors.keys())

        def batches() -> Iterator[list[Tick]]:
            for page in self.reader.iter_pages(query, self.pagination_key):
                yield ukf.push(page)
            yield ukf.flush()

        for ticks in batches():
            if ticks:
                assert ukf.origin is not None  # set by the first GPS fix
                lat, lon = ukf.origin
                yield pd.DataFrame(ticks).assign(origin_lat=lat, origin_lon=lon)

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """Ticks -> ukf_states rows, with the arrays flattened to lists."""
        arrays = df[["x", "p", "x_pred", "p_pred", "cross_cov"]]
        flat = arrays.map(lambda a: a.ravel().tolist(), na_action="ignore")
        return df.assign(run_id=ctx.run_id, **flat)
