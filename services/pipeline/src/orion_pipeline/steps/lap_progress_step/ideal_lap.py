"""Choosing the laps the ideal lap is picked from, and picking it (docs/lap_progress.md)."""

from collections.abc import Sequence

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    IdealLap,
    mean_distance,
)


def assign_lap_ids(times: pd.Series, laps: pd.DataFrame) -> NDArray[np.int64]:
    """The 'lap_id' of the lap each time falls in.

    A lap covers [start_time, end_time), and the last lap also covers its end.
    Times before the first lap get the first lap.
    """
    starts = laps["start_time"].to_numpy()
    index = np.searchsorted(starts, times.to_numpy(), side="right") - 1
    lap_ids = laps["lap_id"].to_numpy(dtype=np.int64)
    return lap_ids[np.clip(index, 0, len(lap_ids) - 1)]


def lap_durations(times: pd.Series, lap_ids: NDArray[np.int64]) -> pd.Series:
    """Each lap's time in seconds, indexed by `lap_id` in lap order.

    Every lap starts at one of the run's points, so its start is its first point,
    its end is the next lap's start, and the last lap ends at the run's last
    point, the same way the lap step builds them.
    """
    starts = (
        pd.DataFrame({"lap_id": lap_ids, "time": times.to_numpy()})
        .groupby("lap_id", sort=True)["time"]
        .min()
    )
    ends = starts.shift(-1).fillna(times.iloc[-1])
    return (ends - starts).dt.total_seconds()


def choose_laps(durations: pd.Series, *, max_lap_time_ratio: float) -> list[int]:
    """The lap_ids of the complete, normal laps the ideal lap is picked from.

    1. Not the first lap (it includes the drive before the first crossing) or
       the last (it's cut off wherever the run ends).
    2. Not an outlier: no slower than `max_lap_time_ratio` times the median lap
       time of the laps left after 1. That drops laps with long stops or holes
       in the data, and laps merged by a missed crossing.

    Args:
        durations: Output of `lap_durations`.
        max_lap_time_ratio: Slowest allowed lap, as a multiple of the median.

    Returns:
        Empty when no lap qualifies, for example in a run with fewer than 3 laps.
    """
    candidates = durations.iloc[1:-1]
    normal = candidates[candidates <= max_lap_time_ratio * candidates.median()]
    return [int(lap_id) for lap_id in normal.index]


def find_medoid(laps: Sequence[IdealLap]) -> int:
    """The index of the lap the other laps are closest to, on average: the most
    typical line. It is the ideal lap.

    For each lap, every point of the other laps is measured to its nearest point
    on it, and the lap with the smallest average distance wins.
    """
    if len(laps) == 1:
        return 0

    def spread(i: int) -> float:
        others = [lap for j, lap in enumerate(laps) if j != i]
        x = np.concatenate([lap.x for lap in others])
        y = np.concatenate([lap.y for lap in others])
        return mean_distance(laps[i], x, y)

    return min(range(len(laps)), key=spread)
