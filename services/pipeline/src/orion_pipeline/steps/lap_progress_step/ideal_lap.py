"""Choosing the laps the ideal lap is picked from, and picking it (docs/lap_progress.md)."""

from collections.abc import Sequence

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    FloatArray,
    IdealLap,
    mean_distance,
    resample,
    smooth_loop,
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

    Every lap starts at one of the run's points, so its start is its first point
    and its end is the next lap's start. The last lap's time is NaN: it's never
    chosen (see `choose_laps`).
    """
    starts = (
        pd.DataFrame({"lap_id": lap_ids, "time": times.to_numpy()})
        .groupby("lap_id", sort=True)["time"]
        .min()
    )
    ends = starts.shift(-1)
    return (ends - starts).dt.total_seconds()


def choose_laps(durations: pd.Series, *, max_lap_time_ratio: float) -> list[int]:
    """The `lap_id`s the ideal lap may be picked from.

    Skips the first and last laps (out-lap and in-lap), and any lap more than
    `max_lap_time_ratio` times slower or faster than the median. A slow lap
    has a long stop or merged laps; a fast one is part of a lap split by a
    false crossing.
    """
    candidates = durations.iloc[1:-1]
    median = candidates.median()
    normal = candidates[
        (candidates <= max_lap_time_ratio * median)
        & (candidates >= median / max_lap_time_ratio)
    ]
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


def build_ideal_lap(
    x: FloatArray,
    y: FloatArray,
    times: pd.Series,
    lap_ids: NDArray[np.int64],
    *,
    max_lap_time_ratio: float,
) -> IdealLap | None:
    chosen = choose_laps(
        lap_durations(times, lap_ids), max_lap_time_ratio=max_lap_time_ratio
    )
    if not chosen:
        return None
    laps = []
    for lap_id in chosen:
        in_lap = lap_ids == lap_id
        laps.append(resample(x[in_lap], y[in_lap]))
    return smooth_loop(laps[find_medoid(laps)])
