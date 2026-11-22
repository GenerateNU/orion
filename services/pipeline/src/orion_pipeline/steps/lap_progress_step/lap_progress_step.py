from collections.abc import Iterator

import numpy as np
import pandas as pd

from orion_core.queries.orion_queries import select_estimated_positions, select_laps
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.lap_progress_step.ideal_lap import (
    assign_lap_ids,
    build_ideal_lap,
)
from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    match_to_ideal_lap,
    percent_of_lap,
)
from orion_pipeline.steps.lap_step.lap_utils import to_local_xy
from orion_pipeline.steps.step_registry import register_step


@register_step
class LapProgressStep(PipelineStep):
    """Gives every estimated position a percentage around the run's ideal lap.

    DB TABLES: FROM Orion[estimated_car_state, laps] -> TO Orion[lap_progress]

    Schema: FROM [time, lattitude, longitude], [lap_id, start_time, end_time]
    -> TO [run_id, time, lap_id, lap_percent]

    Like the lap step, it reads the whole run at once: the ideal lap needs every
    lap. See docs/lap_progress.md.
    """

    name = "lap_progress_step"
    depends_on = ("lap_step",)
    reads_from = "oriondb"
    output_table = "lap_progress"
    # Required by PipelineStep, but unused: `extract` reads the run in one frame.
    pagination_key = ("time",)

    reader: OrionDBClient

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        """The run's positions as one frame, each with the `lap_id` it falls in.

        Yields nothing if the run has no laps (so no positions either).
        """
        laps = self.reader.read_frame(select_laps(ctx.run_id))
        if laps.empty:
            return
        positions = self.reader.read_frame(select_estimated_positions(ctx.run_id))
        yield positions.assign(lap_id=assign_lap_ids(positions["time"], laps))

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        times = df["time"]
        lap_ids = df["lap_id"].to_numpy(dtype=np.int64)
        x, y = to_local_xy(df["lattitude"], df["longitude"])
        time_s = np.asarray((times - times.iloc[0]).dt.total_seconds(), np.float64)

        # Step 1: Build the ideal lap from the run's complete, normal laps.
        ideal = build_ideal_lap(
            x, y, times, lap_ids, max_lap_time_ratio=ctx.lap_progress_max_lap_time_ratio
        )
        if ideal is None:
            return pd.DataFrame()

        # Step 2: Find how far along the ideal lap each position is, in meters.
        s = match_to_ideal_lap(
            x,
            y,
            time_s,
            ideal,
            min_speed_mps=ctx.lap_progress_min_speed_mps,
            max_offtrack_m=ctx.lap_progress_max_offtrack_m,
        )

        # Step 3: Turn meters along the ideal lap into 0-100% for each lap,
        # dropping matches further ahead than the car could have driven.
        percent = percent_of_lap(s, time_s, lap_ids, ideal.length_m)
        return pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "time": times.to_numpy(),
                "lap_id": lap_ids,
                "lap_percent": percent,
            }
        )
