"""Gives each position a lap percentage using the ideal lap (docs/ideal_lap.md).
Positions are in local x/y meters, in time order."""

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree

from orion_pipeline.steps.lap_progress_step.ideal_lap import IdealLap
from orion_pipeline.steps.lap_step.lap_constants import EARTH_RADIUS_M

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def match_to_ideal_lap(
    x: FloatArray,
    y: FloatArray,
    hx: FloatArray,
    hy: FloatArray,
    on_track: NDArray[np.bool_],
    ideal: IdealLap,
    *,
    max_offtrack_m: float,
    min_heading_dot: float,
    heading_weight_m: float,
) -> FloatArray:
    """Meters along the ideal lap to each point's nearest ideal lap point.

    "Nearest" counts direction too, so the far side of a hairpin never wins.
    NaN for points not on track, too far away, or heading the wrong way.
    """
    # The ideal lap's direction at each point, from its neighbors around the loop.
    tx = np.roll(ideal.x, -1) - np.roll(ideal.x, 1)
    ty = np.roll(ideal.y, -1) - np.roll(ideal.y, 1)
    norm = np.hypot(tx, ty)
    tx, ty = tx / np.where(norm > 0, norm, 1), ty / np.where(norm > 0, norm, 1)

    w = heading_weight_m
    tree = cKDTree(np.column_stack([ideal.x, ideal.y, w * tx, w * ty]))
    _, idx = tree.query(np.column_stack([x, y, w * hx, w * hy]))

    off = np.hypot(ideal.x[idx] - x, ideal.y[idx] - y) > max_offtrack_m
    wrong_way = hx * tx[idx] + hy * ty[idx] < min_heading_dot
    s = ideal.percent[idx] / 100.0 * ideal.length_m
    return np.where(on_track & ~off & ~wrong_way, s, np.nan)


def lap_percentages(
    s: FloatArray, lap_ids: IntArray, length_m: float, gate_margin_m: float
) -> FloatArray:
    """Turn distances along the ideal lap into 0-100%, lap by lap.

    Never goes backwards. Starts at 0 and ends at 100 near the start/finish line
    (within `gate_margin_m`). Merged laps wrap back to 0. NaN stays NaN.
    """
    out = np.full(len(s), np.nan)
    for lap_id in np.unique(lap_ids):
        idx = np.flatnonzero((lap_ids == lap_id) & ~np.isnan(s))
        if idx.size == 0:
            continue
        raw = s[idx]
        step = (np.diff(raw) + length_m / 2) % length_m - length_m / 2
        first = raw[0] - length_m if raw[0] > length_m - gate_margin_m else raw[0]
        unwrapped = np.maximum.accumulate(
            first + np.concatenate(([0.0], np.cumsum(step)))
        )
        percent = 100.0 * (unwrapped % length_m) / length_m
        loops = np.floor(unwrapped[-1] / length_m)
        if loops >= 1 and unwrapped[-1] - loops * length_m < gate_margin_m:
            percent[unwrapped >= loops * length_m] = 100.0
        out[idx] = np.where(unwrapped < 0, 0.0, percent)
    return out


def to_lat_lon(
    x: FloatArray, y: FloatArray, origin_lat: float, origin_lon: float
) -> tuple[FloatArray, FloatArray]:
    """Local x/y meters back to latitude/longitude (undoes `to_local_xy`)."""
    lat = origin_lat + np.degrees(y / EARTH_RADIUS_M)
    lon = origin_lon + np.degrees(x / (EARTH_RADIUS_M * np.cos(np.radians(origin_lat))))
    return lat, lon
