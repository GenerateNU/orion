from collections.abc import Iterator

import numpy as np
import pandas as pd

from orion_core.queries.orion_queries import select_estimated_positions, select_laps
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    assign_lap_ids,
    build_ideal_lap,
    distance_along,
    lap_percents,
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
        """Build the ideal lap, then measure every position along it.

        Args:
            df: The run's positions in time order, each with its `lap_id`.
            ctx: The job being run.

        Returns:
            One `lap_progress` row per position. Empty if the run has fewer than
            3 laps, since then there's no complete lap to measure along.
        """
        x, y = to_local_xy(df["lattitude"], df["longitude"])
        lap_ids = df["lap_id"].to_numpy(dtype=np.int64)

        ideal = build_ideal_lap(x, y, lap_ids)
        if ideal is None:
            return pd.DataFrame()
        s = distance_along(ideal, x, y)
        percent = lap_percents(s, df["time"], lap_ids, ideal.length_m)

        return pd.DataFrame(
            {
                "run_id": ctx.run_id,
                "time": df["time"].to_numpy(),
                "lap_id": lap_ids,
                "lap_percent": percent,
            }
        )
