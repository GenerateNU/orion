from collections.abc import Iterator

import numpy as np
import pandas as pd

from orion_core.queries.orion_queries import select_estimated_positions, select_laps
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.lap_progress_step.ideal_lap import (
    assign_lap_ids,
    choose_laps,
    find_medoid,
    lap_stats,
    laps_from_ids,
)
from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    drop_forward_jumps,
    lap_percentages,
    match_to_ideal_lap,
    resample,
    smooth_loop,
)
from orion_pipeline.steps.lap_step.lap_utils import headings, to_local_xy
from orion_pipeline.steps.step_registry import register_step


@register_step
class LapProgressStep(PipelineStep):
    """Gives every estimated position a percentage around the run's ideal lap.

    DB TABLES: FROM Orion[estimated_car_state, laps] -> TO Orion[estimated_car_state]

    Schema: FROM [time, lattitude, longitude], [lap_id, start_time, end_time]
    -> TO [time, lap_percent]

    Like the lap step, it reads the whole run at once: the ideal lap needs every
    lap. See docs/lap_progress.md.
    """

    name = "lap_progress_step"
    depends_on = ("lap_step",)
    reads_from = "oriondb"
    output_table = "estimated_car_state"
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
            `time` and `lap_percent` for every position, NaN where the car is off
            track. Empty if no lap qualifies to be the ideal lap (see `choose_laps`).
        """
        times = df["time"]
        lap_ids = df["lap_id"].to_numpy(dtype=np.int64)
        x, y = to_local_xy(df["lattitude"], df["longitude"])
        time_s = np.asarray((times - times.iloc[0]).dt.total_seconds(), np.float64)

        chosen = choose_laps(
            lap_stats(times, laps_from_ids(times, lap_ids)),
            max_gap_s=ctx.lap_progress_max_gap_s,
            max_lap_time_ratio=ctx.lap_progress_max_lap_time_ratio,
        )
        if not chosen:
            return pd.DataFrame(columns=["time", "lap_percent"])

        laps = [
            resample(x[lap_ids == i], y[lap_ids == i], ctx.lap_progress_spacing_m)
            for i in chosen
        ]
        ideal = smooth_loop(
            laps[find_medoid(laps)],
            spacing_m=ctx.lap_progress_spacing_m,
            smoothing_m=ctx.lap_progress_smoothing_m,
        )

        hx, hy = headings(x, y)
        speed = (
            np.hypot(np.gradient(x), np.gradient(y)) / np.gradient(time_s)
            if len(x) > 1
            else np.zeros(len(x))
        )
        on_track = (np.hypot(hx, hy) > 0) & (speed >= ctx.lap_progress_min_speed_mps)

        s = match_to_ideal_lap(
            x,
            y,
            hx,
            hy,
            on_track,
            ideal,
            max_offtrack_m=ctx.lap_progress_max_offtrack_m,
            min_heading_dot=float(
                np.cos(np.radians(ctx.lap_progress_max_heading_diff_deg))
            ),
            heading_weight_m=ctx.lap_progress_heading_weight_m,
        )
        s = drop_forward_jumps(
            s,
            time_s,
            ideal.length_m,
            max_speed_mps=ctx.lap_progress_max_speed_mps,
            jump_margin_m=ctx.lap_progress_jump_margin_m,
        )
        percent = lap_percentages(
            s, lap_ids, ideal.length_m, ctx.lap_progress_gate_margin_m
        )
        return pd.DataFrame({"time": times.to_numpy(), "lap_percent": percent})

    def prepare(self, ctx: RunContext) -> None:
        """Clear the run's `lap_percent`, so a re-run replaces the values."""
        self.writer.set_null_for_run(self.output_table, "lap_percent", ctx.run_id)

    def write(self, df: pd.DataFrame, ctx: RunContext) -> None:
        """Fill in `lap_percent` on the run's existing rows, matched by time."""
        self.writer.update_for_run(self.output_table, ctx.run_id, df)
