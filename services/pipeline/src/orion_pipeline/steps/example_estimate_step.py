from collections.abc import Iterator

import pandas as pd

from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.step_registry import register_step


@register_step
class ExampleEstimateStep(PipelineStep):
    """Example downstream step: reads what ExampleIngestStep wrote to OrionDB.

    The real version is StateEstimationStep (#41).
    """

    name = "example_estimate"
    depends_on = ("example_ingest",)
    reads_from = "oriondb"
    output_table = "vehicle_state"
    pagination_key = ("signal",)

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        # Real: return self.reader.iter_cleaned(ctx.run_id, self.pagination_key)
        page = pd.DataFrame(
            {"run_id": [ctx.run_id], "signal": ["speed"], "value": [12.5]}
        )
        return iter([page])

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        # Real: Kalman filter → 100 Hz latitude/longitude/speed.
        return df.assign(speed_mps=df["value"] * 0.44704)
