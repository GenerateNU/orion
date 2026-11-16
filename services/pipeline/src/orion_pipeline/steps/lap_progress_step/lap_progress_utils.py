"""Paths around the track and matching positions to them (docs/lap_progress.md).
Positions are in local x/y meters, in time order."""

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import splev, splprep
from scipy.spatial import cKDTree

from orion_pipeline.steps.lap_step.lap_utils import distance_driven

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class IdealLap:
    """A closed path around the track, with evenly spaced points from the gate.

    `s[i]` is how far along the path point i is, from 0 at the gate. After its
    last point the path returns to the first, closing the loop at `length_m`.
    """

    x: FloatArray
    y: FloatArray
    s: FloatArray
    length_m: float


def resample(x: FloatArray, y: FloatArray, spacing_m: float) -> IdealLap:
    """The loop through `x, y` (closed back to the first point), redrawn with a
    point every `spacing_m` meters, starting at the first point."""
    xc, yc = np.append(x, x[0]), np.append(y, y[0])
    along = distance_driven(xc, yc)
    length_m = float(along[-1])
    grid = np.arange(0.0, length_m, spacing_m)
    return IdealLap(
        np.interp(grid, along, xc), np.interp(grid, along, yc), grid, length_m
    )


def smooth_loop(path: IdealLap, *, spacing_m: float, smoothing_m: float) -> IdealLap:
    """`path` through a periodic smoothing spline, resampled from its first point.

    The spline strays from the path's points by about `smoothing_m` (RMS), which
    irons out jitter and small hooks without moving the line.
    """
    # A periodic spline treats its last point as the first, so close the loop.
    xc, yc = np.append(path.x, path.x[0]), np.append(path.y, path.y[0])
    tck, _ = splprep([xc, yc], s=len(path.x) * smoothing_m**2, per=1)
    # Sample densely, then resample by distance so the points are evenly spaced.
    u = np.linspace(0.0, 1.0, 10 * len(path.x), endpoint=False)
    dense = np.asarray(splev(u, cast(Any, tck)))
    return resample(dense[0], dense[1], spacing_m)


def mean_distance(path: IdealLap, x: FloatArray, y: FloatArray) -> float:
    """Average distance from each point to its nearest point on `path`, in meters."""
    distances, _ = cKDTree(np.column_stack([path.x, path.y])).query(
        np.column_stack([x, y])
    )
    return float(np.mean(distances))


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
    """Meters along the ideal lap to each point.

    Finds each point's nearest ideal lap point, then places the point between
    it and a neighbor (see `_along`), so the distance changes smoothly instead
    of in steps of the ideal lap's spacing. "Nearest" counts direction too, so the far
    side of a hairpin never wins. NaN for points not on track, too far away, or
    heading the wrong way.
    """
    # The ideal lap's direction at each point, from its neighbors around the loop.
    tx = np.roll(ideal.x, -1) - np.roll(ideal.x, 1)
    ty = np.roll(ideal.y, -1) - np.roll(ideal.y, 1)
    norm = np.hypot(tx, ty)
    tx, ty = tx / np.where(norm > 0, norm, 1), ty / np.where(norm > 0, norm, 1)

    w = heading_weight_m
    tree = cKDTree(np.column_stack([ideal.x, ideal.y, w * tx, w * ty]))
    _, nearest = tree.query(np.column_stack([x, y, w * hx, w * hy]))
    idx = np.asarray(nearest, dtype=np.int64)

    off = np.hypot(ideal.x[idx] - x, ideal.y[idx] - y) > max_offtrack_m
    wrong_way = hx * tx[idx] + hy * ty[idx] < min_heading_dot
    s = _along(x, y, idx, ideal, tx, ty)
    return np.where(on_track & ~off & ~wrong_way, s, np.nan)


def _along(
    x: FloatArray,
    y: FloatArray,
    idx: IntArray,
    ideal: IdealLap,
    tx: FloatArray,
    ty: FloatArray,
) -> FloatArray:
    """Meters along `ideal` of each point, between ideal lap points.

    How far a point is ahead of ideal lap point i, along the lap's direction
    there (`tx`, `ty`), is zero on the line across the track through point i.
    So the point lies between the two neighbors of its nearest point `idx` where
    that sign changes, and its fraction of the way between them comes from
    interpolating the two distances. That is continuous everywhere, even off the
    line in a bend: at the line through point i, both sides give exactly s[i].
    """
    n = len(ideal.x)
    # Segment i runs from point i to i + 1; the last one closes the loop.
    seg_len = np.diff(np.append(ideal.s, ideal.length_m))

    def ahead(i: IntArray) -> FloatArray:
        return (x - ideal.x[i]) * tx[i] + (y - ideal.y[i]) * ty[i]

    start = np.where(ahead(idx) >= 0, idx, (idx - 1) % n)
    before, after = ahead(start), ahead((start + 1) % n)
    span = before - after
    t = np.clip(np.divide(before, span, out=np.zeros_like(span), where=span > 0), 0, 1)
    along: FloatArray = (ideal.s[start] + t * seg_len[start]) % ideal.length_m
    return along


def drop_forward_jumps(
    s: FloatArray,
    time_s: FloatArray,
    length_m: float,
    *,
    max_speed_mps: float,
    jump_margin_m: float,
) -> FloatArray:
    """`s` with impossible forward jumps set to NaN.

    A point is rejected if it's further ahead of the furthest progress so far
    than the car could drive since then: `max_speed_mps` times the time, plus
    `jump_margin_m`. Comparing to the furthest progress, not the previous point,
    means a bad backward match can't make the points after it look like jumps.
    Backward points are kept (`lap_percentages` never goes backwards anyway).
    """
    out = s.copy()
    furthest: float | None = None
    furthest_time = 0.0
    for i in np.flatnonzero(~np.isnan(s)):
        if furthest is None:
            furthest, furthest_time = s[i], time_s[i]
            continue
        # Meters ahead of the furthest point, wrapped around the lap.
        ahead = (s[i] - furthest + length_m / 2) % length_m - length_m / 2
        if ahead > max_speed_mps * (time_s[i] - furthest_time) + jump_margin_m:
            out[i] = np.nan
        elif ahead > 0:
            furthest, furthest_time = s[i], time_s[i]
    return out


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
