import pandas as pd

from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.step_registry import register_step


@register_step
class ExampleIngestStep(PipelineStep):
    """Example first step: reads raw Penelope data and writes cleaned rows.

    The real version is IngestCleanStep (#17).
    """

    name = "example_ingest"
    reads_from = "penelope"
    output_table = "cleaned_data"

    def extract(self, ctx: RunContext) -> pd.DataFrame:
        # Real: return self.reader.fetch_readings(ctx.run_id)
        return pd.DataFrame({"raw_tag": ["VCU/CarState/speed"], "values": [[12.5]]})

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        # Real: map raw tags to clean signal names, unpack values[], fix units.
        return pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "signal": df["raw_tag"].str.lower(),
                "value": df["values"].str[0],
            }
        )
