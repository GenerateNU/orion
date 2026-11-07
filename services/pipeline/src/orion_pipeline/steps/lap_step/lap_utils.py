"""Pure geometry helpers for lap detection (see docs/lap_detection.md).

Positions are numpy arrays of local x/y meters (see `to_local_xy`), in time order.
"""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

from orion_pipeline.steps.lap_step.lap_constants import EARTH_RADIUS_M

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class Gate:
    """The start/finish line: a segment through (x, y), perpendicular to the heading.

    The heading is the unit direction the car drives through the gate, so a
    point is past the gate when it is ahead of (x, y) along the heading.
    """

    x: float
    y: float
    heading_x: float
    heading_y: float
    half_width_m: float


def to_local_xy(lat: ArrayLike, lon: ArrayLike) -> tuple[FloatArray, FloatArray]:
    """Latitude/longitude in degrees to meters east (x) and north (y) of the first point."""
    lat = np.asarray(lat, dtype=np.float64)
    lon = np.asarray(lon, dtype=np.float64)
    if lat.size == 0:
        return lat, lon
    x = EARTH_RADIUS_M * np.radians(lon - lon[0]) * np.cos(np.radians(lat[0]))
    y = EARTH_RADIUS_M * np.radians(lat - lat[0])
    return x, y


def headings(x: FloatArray, y: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Unit direction of travel at each point, from its neighbors.

    (0, 0) where the car isn't moving.
    """
    if len(x) < 2:
        return np.zeros(len(x)), np.zeros(len(y))
    dx, dy = np.gradient(x), np.gradient(y)
    length = np.hypot(dx, dy)
    safe_length = np.where(length > 0, length, 1.0)
    return dx / safe_length, dy / safe_length


def distance_driven(x: FloatArray, y: FloatArray) -> FloatArray:
    """Total distance driven up to each point, in meters. 0 at the first point."""
    steps_m = np.hypot(np.diff(x), np.diff(y))
    return np.concatenate(([0.0], np.cumsum(steps_m)))[: len(x)]


def find_first_revisit(
    x: FloatArray,
    y: FloatArray,
    time_s: FloatArray,
    *,
    hitbox_radius_m: float,
    min_revisit_time_s: float,
    min_revisit_distance_m: float,
) -> int | None:
    """Index of the first earlier point the car drives back over while moving, or None.

    Each point Q, in time order, is checked against the points P before it
    that are at least `min_revisit_time_s` and `min_revisit_distance_m` back.
    The first Q with a moving P inside its hitbox wins, and the P closest to
    Q is returned.
    """
    distance_m = distance_driven(x, y)
    moving = np.hypot(*headings(x, y)) > 0

    # time_s and distance_m only increase, so for each Q the points far enough
    # back are exactly the ones before some index. Binary search finds it.
    time_cut = np.searchsorted(time_s, time_s - min_revisit_time_s, side="right")
    distance_cut = np.searchsorted(
        distance_m, distance_m - min_revisit_distance_m, side="right"
    )
    # Capped at Q's own index, so Q is never compared with itself or later points.
    cutoff = np.minimum.reduce([time_cut, distance_cut, np.arange(len(x))])

    for q in np.flatnonzero(cutoff):
        c = cutoff[q]
        dist_sq = (x[:c] - x[q]) ** 2 + (y[:c] - y[q]) ** 2
        candidates = np.flatnonzero((dist_sq <= hitbox_radius_m**2) & moving[:c])
        if candidates.size:
            return int(candidates[np.argmin(dist_sq[candidates])])
    return None


def find_gate(
    x: FloatArray,
    y: FloatArray,
    time_s: FloatArray,
    *,
    sample_every: int,
    hitbox_radius_m: float,
    min_revisit_time_s: float,
    min_revisit_distance_m: float,
    half_width_m: float,
) -> Gate | None:
    """The gate at the run's first revisit, or None if the car never revisits a spot.

    Only every `sample_every`-th point is searched, to keep the search fast.
    """
    sampled = slice(None, None, sample_every)
    xs, ys = x[sampled], y[sampled]
    p = find_first_revisit(
        xs,
        ys,
        time_s[sampled],
        hitbox_radius_m=hitbox_radius_m,
        min_revisit_time_s=min_revisit_time_s,
        min_revisit_distance_m=min_revisit_distance_m,
    )
    if p is None:
        return None
    hx, hy = headings(xs, ys)
    return Gate(
        x=float(xs[p]),
        y=float(ys[p]),
        heading_x=float(hx[p]),
        heading_y=float(hy[p]),
        half_width_m=half_width_m,
    )


def find_crossings(x: FloatArray, y: FloatArray, gate: Gate) -> NDArray[np.intp]:
    """For every forward pass through the gate, the index of the first point past it."""
    dx, dy = x - gate.x, y - gate.y
    # Signed distance ahead of the gate's line, and left of the gate's center.
    ahead = dx * gate.heading_x + dy * gate.heading_y
    left = dy * gate.heading_x - dx * gate.heading_y

    before, after = ahead[:-1], ahead[1:]
    forward = (before < 0) & (after >= 0)
    # How far along each forward step the line is reached, from 0 to 1.
    t = np.divide(before, before - after, out=np.zeros_like(before), where=forward)
    left_at_line = left[:-1] + t * (left[1:] - left[:-1])

    return np.flatnonzero(forward & (np.abs(left_at_line) <= gate.half_width_m)) + 1


def apply_min_lap_time(
    start_time: datetime, crossing_times: list[datetime], min_lap_time_s: float
) -> list[datetime]:
    """Drop crossings less than `min_lap_time_s` after the previous lap boundary.

    The first boundary is `start_time`, so a crossing right after the run
    starts is dropped too. Dropped crossings don't become boundaries.
    """
    kept: list[datetime] = []
    last_boundary = start_time
    for crossing in crossing_times:
        if (crossing - last_boundary).total_seconds() >= min_lap_time_s:
            kept.append(crossing)
            last_boundary = crossing
    return kept


def build_lap_rows(
    run_id: str,
    start_time: datetime,
    end_time: datetime,
    crossing_times: list[datetime],
) -> pd.DataFrame:
    """One lap per crossing, numbered from 1, plus a last lap ending at `end_time`.

    Lap 1 starts at `start_time`. If the last crossing is `end_time`, no
    empty lap is added after it.
    """
    lap_ends = list(crossing_times)
    if not lap_ends or lap_ends[-1] != end_time:
        lap_ends.append(end_time)
    return pd.DataFrame(
        {
            "run_id": run_id,
            "lap_id": range(1, len(lap_ends) + 1),
            "start_time": [start_time, *lap_ends[:-1]],
            "end_time": lap_ends,
        }
    )
