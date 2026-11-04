from collections.abc import Iterator
from datetime import datetime

import numpy as np
import pandas as pd

from orion_core.queries.orion_queries import select_estimated_positions
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.lap_step.lap_utils import (
    apply_min_lap_time,
    build_lap_rows,
    find_crossings,
    find_gate,
    to_local_xy,
)
from orion_pipeline.steps.step_registry import register_step


@register_step
class LapStep(PipelineStep):
    """Splits a run into laps at a start/finish gate found from the car's path.

    Unlike other steps, this one reads the whole run at once instead of
    paging. It only needs three columns (time, lat, lon), and finding the gate
    and counting laps over one frame needs no state carried between pages.
    """

    name = "lap_step"
    depends_on = ("state_step",)
    reads_from = "oriondb"
    output_table = "laps"
    # Required by PipelineStep, but unused: `extract` reads the run in one frame.
    pagination_key = ("time",)

    # The reader for the lap step will always be OrionDBClient and never PenelopeClient
    reader: OrionDBClient

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        """The whole run as a single frame, or nothing if the run has no rows."""
        df = self.reader.read_frame(select_estimated_positions(ctx.run_id))
        if not df.empty:
            yield df

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """Find the gate, then cut a lap at every crossing of it.

        Args:
            df: The run's estimated_car_state rows, in time order. Not empty.
            ctx: The job being run.

        Returns:
            One row per lap. The last lap ends at the run's last point.
        """
        times = df["time"]
        start_time: datetime = times.iloc[0]
        end_time: datetime = times.iloc[-1]

        x, y = to_local_xy(df["lattitude"], df["longitude"])
        time_s = np.asarray((times - start_time).dt.total_seconds(), dtype=np.float64)
        gate = find_gate(
            x,
            y,
            time_s,
            sample_every=ctx.lap_gate_search_sample_every,
            hitbox_radius_m=ctx.lap_hitbox_radius_m,
            min_revisit_time_s=ctx.lap_min_revisit_time_s,
            min_revisit_distance_m=ctx.lap_min_revisit_distance_m,
            half_width_m=ctx.lap_gate_half_width_m,
        )

        crossing_times: list[datetime] = []
        if gate is not None:
            all_crossings = times.iloc[find_crossings(x, y, gate)].tolist()
            crossing_times = apply_min_lap_time(
                start_time, all_crossings, ctx.lap_min_lap_time_s
            )

        return build_lap_rows(ctx.run_id, start_time, end_time, crossing_times)
