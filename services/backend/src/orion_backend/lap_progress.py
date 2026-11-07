"""How far through its lap the car is at each point (see docs/lap_progress.md)."""

from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from orion_core.geometry import distance_driven, to_local_xy
from orion_core.models.orion import Lap

FloatArray = NDArray[np.float64]

RESAMPLE_STEP_M = 1.0


def reference_lap(laps: Sequence[Lap]) -> Lap:
    """The median lap by lap time. Of two middle laps, the one with the lower lap_id."""
    by_time = sorted(laps, key=lambda lap: lap.end_time - lap.start_time)
    middle = by_time[(len(by_time) - 1) // 2 : len(by_time) // 2 + 1]
    return min(middle, key=lambda lap: lap.lap_id)


def lap_progress(
    lat: ArrayLike, lon: ArrayLike, ref_lat: ArrayLike, ref_lon: ArrayLike
) -> FloatArray:
    """For each point, the share (0 to 1) of the reference lap's distance at the
    nearest point of the reference, resampled every `RESAMPLE_STEP_M`.
    """
    n = len(np.asarray(ref_lat))
    x, y = to_local_xy(np.concatenate([ref_lat, lat]), np.concatenate([ref_lon, lon]))
    ref_x, ref_y, x, y = x[:n], y[:n], x[n:], y[n:]

    distance = distance_driven(ref_x, ref_y)
    count = int(np.ceil(distance[-1] / RESAMPLE_STEP_M)) + 1
    steps = np.linspace(0.0, distance[-1], count)
    step_x = np.interp(steps, distance, ref_x)
    step_y = np.interp(steps, distance, ref_y)

    dist_sq = (x[:, None] - step_x) ** 2 + (y[:, None] - step_y) ** 2
    return np.linspace(0.0, 1.0, count)[np.argmin(dist_sq, axis=1)]
