"""Helpers for the lap progress step (see docs/lap_progress.md).

Positions are numpy arrays of local x/y meters (see `to_local_xy`), in time order.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.interpolate import splev, splprep
from scipy.spatial import cKDTree

from orion_pipeline.steps.lap_step.lap_utils import distance_driven, headings

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

# Distance between the points of the ideal lap, in meters.
SPACING_M = 1.0
# How far, as an RMS, smoothing may move the ideal lap off the medoid lap's points
# to iron out GPS jitter, in meters.
SMOOTHING_M = 0.25
# A lap longer than this times the median lap can't be the ideal lap: it's two laps
# merged by a missed crossing.
MAX_LAP_LENGTH_RATIO = 1.5
# When matching, each unit of heading counts as this many meters, so the far side of
# a hairpin (driven the other way) never looks nearest.
HEADING_WEIGHT_M = 10.0
# A match further ahead of the lap's progress than the car could drive since then,
# at this speed (m/s) plus this much slack (m), is a bad match and doesn't count.
MAX_SPEED_MPS = 40.0
JUMP_MARGIN_M = 10.0


@dataclass(frozen=True)
class IdealLap:
    """A closed path around the track, with evenly spaced points from the line.

    `s[i]` is how far along the path point i is, from 0 at the start/finish line.
    After its last point the path returns to the first, closing the loop at
    `length_m`.
    """

    x: FloatArray
    y: FloatArray
    s: FloatArray
    length_m: float


def assign_lap_ids(times: pd.Series, laps: pd.DataFrame) -> IntArray:
    """The `lap_id` of the lap each time falls in.

    A lap covers [start_time, end_time), and the last lap also covers its end.
    """
    starts = laps["start_time"].to_numpy()
    index = np.searchsorted(starts, times.to_numpy(), side="right") - 1
    lap_ids = laps["lap_id"].to_numpy(dtype=np.int64)
    return lap_ids[np.clip(index, 0, len(lap_ids) - 1)]


def build_ideal_lap(x: FloatArray, y: FloatArray, lap_ids: IntArray) -> IdealLap | None:
    """The lap every point is measured along: the most typical of the run's middle
    laps, lightly smoothed. None if the run has no middle lap (fewer than 3 laps)."""
    laps = middle_laps(x, y, lap_ids)
    if not laps:
        return None
    return smooth_loop(laps[find_medoid(laps)])


def middle_laps(x: FloatArray, y: FloatArray, lap_ids: IntArray) -> list[IdealLap]:
    """Every lap but the first (it starts in the pits) and the last (it stops
    wherever the run stops), resampled, minus merged laps: those longer than
    `MAX_LAP_LENGTH_RATIO` times the median."""
    middle_ids = np.unique(lap_ids)[1:-1]
    laps = [resample(x[lap_ids == i], y[lap_ids == i]) for i in middle_ids]
    if not laps:
        return []
    longest_m = MAX_LAP_LENGTH_RATIO * np.median([lap.length_m for lap in laps])
    return [lap for lap in laps if lap.length_m <= longest_m]


def resample(x: FloatArray, y: FloatArray, spacing_m: float = SPACING_M) -> IdealLap:
    """The loop through `x, y` (closed back to the first point), redrawn with a
    point every `spacing_m` meters, starting at the first point."""
    xc, yc = np.append(x, x[0]), np.append(y, y[0])
    along = distance_driven(xc, yc)
    length_m = float(along[-1])
    grid = np.arange(0.0, length_m, spacing_m)
    return IdealLap(
        np.interp(grid, along, xc), np.interp(grid, along, yc), grid, length_m
    )


def find_medoid(laps: Sequence[IdealLap]) -> int:
    """The index of the lap the other laps are closest to, on average: the most
    typical line.

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


def mean_distance(path: IdealLap, x: FloatArray, y: FloatArray) -> float:
    """Average distance from each point to its nearest point on `path`, in meters."""
    distances, _ = cKDTree(np.column_stack([path.x, path.y])).query(
        np.column_stack([x, y])
    )
    return float(np.mean(distances))


def smooth_loop(path: IdealLap) -> IdealLap:
    """`path` through a periodic smoothing spline, resampled from its first point.

    The spline strays from the path's points by about `SMOOTHING_M` (RMS), which
    irons out jitter and small hooks without moving the line.
    """
    # A periodic spline treats its last point as the first, so close the loop.
    xc, yc = np.append(path.x, path.x[0]), np.append(path.y, path.y[0])
    tck, _ = splprep([xc, yc], s=len(path.x) * SMOOTHING_M**2, per=1)
    # Sample densely, then resample by distance so the points are evenly spaced.
    u = np.linspace(0.0, 1.0, 10 * len(path.x), endpoint=False)
    dense = np.asarray(splev(u, cast(Any, tck)))
    return resample(dense[0], dense[1])


def distance_along(ideal: IdealLap, x: FloatArray, y: FloatArray) -> FloatArray:
    """Meters along the ideal lap to each point.

    Each point is matched to its nearest ideal lap point, where heading counts too
    (see `HEADING_WEIGHT_M`), then placed along the ideal lap's direction there, so
    the distance changes smoothly instead of in `SPACING_M` steps.
    """
    hx, hy = headings(x, y)
    tx, ty = loop_directions(ideal)
    w = HEADING_WEIGHT_M
    tree = cKDTree(np.column_stack([ideal.x, ideal.y, w * tx, w * ty]))
    _, nearest = tree.query(np.column_stack([x, y, w * hx, w * hy]))
    i = np.asarray(nearest, dtype=np.int64)
    ahead = (x - ideal.x[i]) * tx[i] + (y - ideal.y[i]) * ty[i]
    along: FloatArray = (ideal.s[i] + ahead) % ideal.length_m
    return along


def loop_directions(path: IdealLap) -> tuple[FloatArray, FloatArray]:
    """Unit direction of `path` at each point, from its neighbors around the loop."""
    dx = np.roll(path.x, -1) - np.roll(path.x, 1)
    dy = np.roll(path.y, -1) - np.roll(path.y, 1)
    length = np.hypot(dx, dy)
    return dx / length, dy / length


def lap_percents(
    s: FloatArray, times: pd.Series, lap_ids: IntArray, length_m: float
) -> FloatArray:
    """Turn meters along the ideal lap into 0-100% of each lap.

    Within a lap the percentage never goes back: each point is compared to the
    lap's progress so far, and only moves it forward. A match further ahead than
    the car could have driven since then (`MAX_SPEED_MPS`, `JUMP_MARGIN_M`) is a bad
    match, so that point keeps the previous percentage.
    """
    time_s = (times - times.iloc[0]).dt.total_seconds().to_numpy()
    progress = np.empty(len(s))
    progress_m = progress_time = 0.0
    for i in range(len(s)):
        if i == 0 or lap_ids[i] != lap_ids[i - 1]:
            # A lap starts at the line, so a point more than half a lap "ahead" is
            # really just before the line.
            progress_m = s[i] - length_m if s[i] > length_m / 2 else s[i]
            progress_time = time_s[i]
        else:
            ahead = wrap_around_lap(s[i] - progress_m, length_m)
            reachable = MAX_SPEED_MPS * (time_s[i] - progress_time) + JUMP_MARGIN_M
            if 0 < ahead <= reachable:
                progress_m, progress_time = progress_m + ahead, time_s[i]
        progress[i] = progress_m
    return np.clip(100.0 * progress / length_m, 0.0, 100.0)


def wrap_around_lap(d: float, length_m: float) -> float:
    """`d` meters wrapped around a lap of `length_m`, into [-length_m / 2, length_m / 2)."""
    return (d + length_m / 2) % length_m - length_m / 2
