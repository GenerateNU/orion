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


def laps_from_ids(times: pd.Series, lap_ids: NDArray[np.int64]) -> pd.DataFrame:
    """The 'laps' rows ('lap_id', 'start_time', 'end_time') behind each point's lap_id.

    Every lap starts at one of the run's points, so its start is its first point,
    its end is the next lap's start, and the last lap ends at the run's last
    point, the same way the lap step builds them.
    """
    first = pd.DataFrame({"lap_id": lap_ids, "time": times.to_numpy()}).groupby(
        "lap_id", sort=True
    )["time"]
    starts = first.min()
    ends = starts.shift(-1).fillna(times.iloc[-1])
    return pd.DataFrame(
        {
            "lap_id": starts.index.to_numpy(dtype=np.int64),
            "start_time": starts.to_numpy(),
            "end_time": ends.to_numpy(),
        }
    )


def lap_stats(times: pd.Series, laps: pd.DataFrame) -> pd.DataFrame:
    """Each lap's time and longest hole in its data.

    Args:
        times: The run's point times, in order.
        laps: The run's 'laps' rows, in order.

    Returns:
        'laps' with 'duration_s' and 'max_gap_s' added. The gap counts the edges
        too: lap start to first point, and last point to lap end. A lap with no
        points has an infinite gap.
    """
    starts = pd.DatetimeIndex(laps["start_time"])
    ends = pd.DatetimeIndex(laps["end_time"])
    gaps: list[float] = []
    for i in range(len(laps)):
        inside = times[(times >= starts[i]) & (times < ends[i])]
        if inside.empty:
            gaps.append(np.inf)
            continue
        edges = pd.Series([starts[i], *inside, ends[i]])
        gaps.append(float(edges.diff().dt.total_seconds().max()))
    return laps.assign(duration_s=(ends - starts).total_seconds(), max_gap_s=gaps)


def choose_laps(
    stats: pd.DataFrame, *, max_gap_s: float, max_lap_time_ratio: float
) -> list[int]:
    """The lap_ids of the complete, normal laps the ideal lap is picked from.

    1. Not the first lap (it includes the drive before the first crossing) or
       the last (it's cut off wherever the run ends).
    2. No hole in the data longer than `max_gap_s`.
    3. Not an outlier: no slower than `max_lap_time_ratio` times the median lap
       time of the laps left after 1 and 2. That drops laps with long stops and
       laps merged by a missed crossing.

    Args:
        stats: Output of `lap_stats`, in lap order.
        max_gap_s: Longest allowed hole in a lap's data, in seconds.
        max_lap_time_ratio: Slowest allowed lap, as a multiple of the median.

    Returns:
        Empty when no lap qualifies, for example in a run with fewer than 3 laps.
    """
    candidates = stats.iloc[1:-1]
    full_data = candidates[candidates["max_gap_s"] <= max_gap_s]
    limit_s = max_lap_time_ratio * full_data["duration_s"].median()
    normal = full_data[full_data["duration_s"] <= limit_s]
    return [int(lap_id) for lap_id in normal["lap_id"]]


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
