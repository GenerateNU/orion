from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd

from orion_core.queries.orion_queries import select_estimated_positions, select_laps
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.lap_progress_step import lap_progress_constants as tune
from orion_pipeline.steps.lap_progress_step.ideal_lap import (
    assign_lap_ids,
    build_ideal_lap,
    gate_at,
)
from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    lap_percentages,
    match_to_ideal_lap,
    to_lat_lon,
)
from orion_pipeline.steps.lap_step.lap_utils import (
    Gate,
    find_gate,
    headings,
    to_local_xy,
)
from orion_pipeline.steps.step_registry import register_step

IDEAL_LAP_TABLE = "ideal_lap_points"


@dataclass(frozen=True)
class LapProgressOutput:
    """Both tables the step writes, for one run."""

    progress: pd.DataFrame
    ideal_lap: pd.DataFrame


@register_step
class LapProgressStep(PipelineStep):
    """Gives every estimated position a percentage around the run's ideal lap.

    DB TABLES: FROM Orion[estimated_car_state, laps]
    -> TO Orion[lap_progress, ideal_lap_points]

    Like the lap step, it reads the whole run at once: picking the ideal lap
    needs every lap. See docs/ideal_lap.md.
    """

    name = "lap_progress_step"
    depends_on = ("lap_step",)
    reads_from = "oriondb"
    output_table = "lap_progress"
    # Required by PipelineStep, but unused: `extract` reads the run in one frame.
    pagination_key = ("time",)

    reader: OrionDBClient

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        """The run's positions as one frame, each with the lap it falls in: its
        `lap_id`, `lap_start` and `lap_end`.

        The ideal lap needs each lap's exact start and end times, so they're
        added as columns. Every lap starts at one of the run's positions, so
        every lap has at least one row. Yields nothing if the run has no
        positions or no laps.
        """
        positions = self.reader.read_frame(select_estimated_positions(ctx.run_id))
        if positions.empty:
            return
        laps = self.reader.read_frame(select_laps(ctx.run_id))
        if laps.empty:
            return
        positions["lap_id"] = assign_lap_ids(positions["time"], laps)
        lap_times = laps.rename(
            columns={"start_time": "lap_start", "end_time": "lap_end"}
        )
        yield positions.merge(lap_times, on="lap_id", how="left")

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """The `lap_progress` rows only. `run` uses `transform_all` for both tables."""
        return self.transform_all(df, ctx).progress

    def transform_all(self, df: pd.DataFrame, ctx: RunContext) -> LapProgressOutput:
        """Build the ideal lap, then match every position to it.

        Args:
            df: The run's positions in time order, each with its `lap_id`,
                `lap_start` and `lap_end` (see `extract`).
            ctx: The job being run.

        Returns:
            Empty frames if the run has no ideal lap (see `build_ideal_lap`): no lap
            or loop through the gate with full data.
        """
        # The laps table again, one row per lap, from the columns `extract` added.
        laps = (
            df.groupby("lap_id", sort=True)[["lap_start", "lap_end"]]
            .first()
            .reset_index()
            .rename(columns={"lap_start": "start_time", "lap_end": "end_time"})
        )
        times = df["time"]
        lap_ids = df["lap_id"].to_numpy(dtype=np.int64)
        x, y = to_local_xy(df["lattitude"], df["longitude"])
        time_s = np.asarray((times - times.iloc[0]).dt.total_seconds(), np.float64)
        positions = pd.DataFrame({"time": times, "x": x, "y": y})

        def fallback_gate() -> Gate | None:
            # Where the lap step's gate is, if any lap ends there (the start of
            # lap 2). Otherwise found the way the lap step finds its gate. Either
            # way wider, since lines spread out at the gate.
            half_width_m = tune.MAX_OFFTRACK_M
            if len(laps) >= 2:
                start = int(np.argmax(lap_ids == laps["lap_id"].iloc[1]))
                return gate_at(positions, start, half_width_m)
            return find_gate(
                x,
                y,
                time_s,
                sample_every=ctx.lap_gate_search_sample_every,
                hitbox_radius_m=ctx.lap_hitbox_radius_m,
                min_revisit_time_s=ctx.lap_min_revisit_time_s,
                min_revisit_distance_m=ctx.lap_min_revisit_distance_m,
                half_width_m=half_width_m,
            )

        ideal = build_ideal_lap(
            positions,
            laps,
            max_gap_s=tune.MAX_GAP_S,
            max_length_ratio=tune.MAX_LENGTH_RATIO,
            spacing_m=tune.PATH_SPACING_M,
            fallback_gate=fallback_gate,
            min_loop_time_s=ctx.lap_min_lap_time_s,
        )
        if ideal is None:
            return LapProgressOutput(pd.DataFrame(), pd.DataFrame())

        hx, hy = headings(x, y)
        speed = (
            np.hypot(np.gradient(x), np.gradient(y)) / np.gradient(time_s)
            if len(x) > 1
            else np.zeros(len(x))
        )
        on_track = (np.hypot(hx, hy) > 0) & (speed >= tune.MIN_SPEED_MPS)

        s = match_to_ideal_lap(
            x,
            y,
            hx,
            hy,
            on_track,
            ideal,
            max_offtrack_m=tune.MAX_OFFTRACK_M,
            min_heading_dot=float(np.cos(np.radians(tune.MAX_HEADING_DIFF_DEG))),
            heading_weight_m=tune.HEADING_WEIGHT_M,
        )
        percent = lap_percentages(s, lap_ids, ideal.length_m, tune.GATE_MARGIN_M)

        progress = pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "time": times.to_numpy(),
                "lap_id": lap_ids,
                # Off-track points as None, so they're written as NULL, not NaN.
                # dtype=object keeps them None: pandas turns a mixed list of
                # numbers and None back into NaN.
                "lap_percent": pd.Series(
                    [None if np.isnan(p) else p for p in percent], dtype=object
                ),
            }
        )
        lat, lon = to_lat_lon(
            ideal.x,
            ideal.y,
            float(df["lattitude"].iloc[0]),
            float(df["longitude"].iloc[0]),
        )
        ideal_lap = pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "seq": np.arange(len(ideal.x)),
                "latitude": lat,
                "longitude": lon,
                "lap_percent": ideal.percent,
            }
        )
        return LapProgressOutput(progress, ideal_lap)

    def prepare(self, ctx: RunContext) -> None:
        """Clear both output tables, so a re-run replaces the run's rows."""
        self.writer.delete_for_run(self.output_table, ctx.run_id)
        self.writer.delete_for_run(IDEAL_LAP_TABLE, ctx.run_id)

    def run(self, ctx: RunContext) -> None:
        """Like `PipelineStep.run`, but writes both tables from one transform."""
        self.prepare(ctx)
        for page in self.extract(ctx):
            output = self.transform_all(page, ctx)
            self.writer.append(IDEAL_LAP_TABLE, output.ideal_lap)
            self.writer.append(self.output_table, output.progress)
