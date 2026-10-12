from collections.abc import Iterator

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
    pagination_key = ("time", "raw_tag")

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        # Real: return self.reader.iter_readings(
        #     ctx.run_id, self.pagination_key, self.page_size
        # )
        page = pd.DataFrame(
            {"time": [0.0], "raw_tag": ["VCU/CarState/speed"], "values": [[12.5]]}
        )
        return iter([page])

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        # Real: map raw tags to clean signal names, unpack values[], fix units.
        return pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "signal": df["raw_tag"].str.lower(),
                "value": df["values"].str[0],
            }
        )
