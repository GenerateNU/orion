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
    choose_laps,
    lap_durations,
)
from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    drop_forward_jumps,
    lap_percentages,
    match_to_ideal_lap,
    seconds_since_start,
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

        Yields nothing if the run has no positions or no laps.
        """
        positions = self.reader.read_frame(select_estimated_positions(ctx.run_id))
        if positions.empty:
            return
        laps = self.reader.read_frame(select_laps(ctx.run_id))
        if laps.empty:
            return
        yield positions.assign(lap_id=assign_lap_ids(positions["time"], laps))

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """Pick the ideal lap (the medoid of the chosen laps, lightly smoothed),
        then match every position to it.

        Args:
            df: The run's positions in time order, each with its `lap_id`.
            ctx: The job being run.

        Returns:
            `lap_progress` rows (`run_id`, `time`, `lap_id`, `lap_percent`) for
            every position, `lap_percent` NaN where the car is off track. Empty if
            no lap qualifies to be the ideal lap (see `choose_laps`).
        """
        times = df["time"]
        lap_ids = df["lap_id"].to_numpy(dtype=np.int64)
        x, y = to_local_xy(df["lattitude"], df["longitude"])
        time_s = seconds_since_start(times)

        # Step 1: Pick the complete, normal laps the ideal lap can come from.
        chosen = choose_laps(
            lap_durations(times, lap_ids),
            max_lap_time_ratio=ctx.lap_progress_max_lap_time_ratio,
        )
        if not chosen:
            return pd.DataFrame(columns=["run_id", "time", "lap_id", "lap_percent"])

        # Step 2: Build the ideal lap from the most typical of them.
        ideal = build_ideal_lap(
            x,
            y,
            lap_ids,
            chosen,
            spacing_m=ctx.lap_progress_spacing_m,
            smoothing_m=ctx.lap_progress_smoothing_m,
        )

        # Step 3: Find how far along the ideal lap each position is, in meters.
        s = match_to_ideal_lap(
            x,
            y,
            time_s,
            ideal,
            min_speed_mps=ctx.lap_progress_min_speed_mps,
            max_offtrack_m=ctx.lap_progress_max_offtrack_m,
            max_heading_diff_deg=ctx.lap_progress_max_heading_diff_deg,
            heading_weight_m=ctx.lap_progress_heading_weight_m,
        )

        # Step 4: Drop matches further ahead than the car could have driven.
        s = drop_forward_jumps(
            s,
            time_s,
            ideal.length_m,
            max_speed_mps=ctx.lap_progress_max_speed_mps,
            jump_margin_m=ctx.lap_progress_jump_margin_m,
        )

        # Step 5: Turn meters along the ideal lap into 0-100% for each lap.
        percent = lap_percentages(
            s, lap_ids, ideal.length_m, ctx.lap_progress_gate_margin_m
        )
        return pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "time": times.to_numpy(),
                "lap_id": lap_ids,
                "lap_percent": percent,
            }
        )
