"""Paths around the track and matching positions to them (docs/lap_progress.md).
Positions are in local x/y meters, in time order."""

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import splev, splprep
from scipy.spatial import cKDTree

from orion_pipeline.steps.lap_step.lap_utils import distance_driven, headings

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
# Distance between the points of the ideal lap, in meters.
SPACING_M = 1.0
# How far, as an RMS, smoothing may move the ideal lap off the medoid lap's points
# to iron out jitter, in meters.
SMOOTHING_M = 0.25
# Points heading more than this far from the ideal lap's direction are off track
# (spins, wrong way), in degrees.
MAX_HEADING_DIFF_DEG = 60.0
# When matching, each unit of heading counts as this many meters, so a full
# turn-around adds 2 x this to the distance and the far side of a hairpin (driven
# the other way) never looks closest.
HEADING_WEIGHT_M = 10.0
# A lap's first points within this many meters before the start/finish line read
# 0%, and its last points within this many meters past it read 100%.
GATE_MARGIN_M = 20.0
# A match further ahead of the car's furthest progress than it could drive at this
# speed (m/s), plus `JUMP_MARGIN_M` (m) of slack for matching noise, is a bad match
MAX_SPEED_MPS = 40.0
JUMP_MARGIN_M = 10.0


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


def smooth_loop(
    path: IdealLap, *, spacing_m: float = SPACING_M, smoothing_m: float = SMOOTHING_M
) -> IdealLap:
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
    time_s: FloatArray,
    ideal: IdealLap,
    *,
    min_speed_mps: float,
    max_offtrack_m: float,
    max_heading_diff_deg: float = MAX_HEADING_DIFF_DEG,
    heading_weight_m: float = HEADING_WEIGHT_M,
) -> FloatArray:
    """Meters along the ideal lap to each point."""
    hx, hy = headings(x, y)
    moving = np.hypot(np.gradient(x), np.gradient(y)) >= min_speed_mps * np.gradient(
        time_s
    )
    min_heading_dot = np.cos(np.radians(max_heading_diff_deg))

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
    s = _project_onto_ideal_lap(x, y, idx, ideal, tx, ty)
    return np.where(moving & ~off & ~wrong_way, s, np.nan)


def _project_onto_ideal_lap(
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


def _wrap_around_lap(d: float, length_m: float) -> float:
    """`d` meters wrapped around a lap of `length_m`, into [-length_m / 2, length_m / 2)."""
    return (d + length_m / 2) % length_m - length_m / 2


def percent_of_lap(
    s: FloatArray,
    time_s: FloatArray,
    lap_ids: IntArray,
    length_m: float,
    *,
    max_speed_mps: float = MAX_SPEED_MPS,
    jump_margin_m: float = JUMP_MARGIN_M,
    gate_margin_m: float = GATE_MARGIN_M,
) -> FloatArray:
    """Turn distances along the ideal lap into 0-100%, lap by lap.

    Each point is measured against the furthest progress so far, not against
    the point before it, so one bad match can't throw off the points after it
    """
    # Meters into each point's lap, counted past length_m for merged laps.
    progress = np.full(len(s), np.nan)
    furthest: float | None = None  # The run's furthest `s`, for the jump check.
    furthest_time = 0.0
    lap: int | None = None
    lap_progress = 0.0
    for i in np.flatnonzero(~np.isnan(s)):
        if furthest is not None:
            ahead = _wrap_around_lap(s[i] - furthest, length_m)
            if ahead > max_speed_mps * (time_s[i] - furthest_time) + jump_margin_m:
                continue
            if ahead > 0:
                furthest, furthest_time = s[i], time_s[i]
        else:
            furthest, furthest_time = s[i], time_s[i]

        if lap_ids[i] != lap:
            # A lap's first point just before the gate starts below 0.
            lap = int(lap_ids[i])
            near_gate = s[i] > length_m - gate_margin_m
            lap_progress = s[i] - length_m if near_gate else s[i]
        else:
            lap_progress += max(_wrap_around_lap(s[i] - lap_progress, length_m), 0.0)
        progress[i] = lap_progress

    percent = 100.0 * (progress % length_m) / length_m
    percent[progress < 0] = 0.0
    # A lap that ends just past the gate reads 100 from the gate on.
    for lap_id in np.unique(lap_ids):
        in_lap = (lap_ids == lap_id) & ~np.isnan(progress)
        if not in_lap.any():
            continue
        last = progress[in_lap][-1]
        loops = np.floor(last / length_m)
        if loops >= 1 and last - loops * length_m < gate_margin_m:
            percent[in_lap & (progress >= loops * length_m)] = 100.0
    return percent
