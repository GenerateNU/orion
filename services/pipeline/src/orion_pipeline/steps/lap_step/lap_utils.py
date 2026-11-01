"""Pure geometry helpers for lap detection (see docs/lap_detection.md)."""

import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from orion_pipeline.steps.lap_step.lap_constants import EARTH_RADIUS_M


@dataclass(frozen=True)
class Gate:
    """The start/finish line from left end G1 to right end G2, facing forward."""

    g1_x: float
    g1_y: float
    g2_x: float
    g2_y: float


@dataclass
class VisitedPoints:
    """Every point sampled while searching for the gate, in time order."""

    x: NDArray[np.float64] = field(default_factory=lambda: np.empty(0))
    y: NDArray[np.float64] = field(default_factory=lambda: np.empty(0))
    time_s: NDArray[np.float64] = field(default_factory=lambda: np.empty(0))
    distance_m: NDArray[np.float64] = field(default_factory=lambda: np.empty(0))


@dataclass(frozen=True)
class TrackPoint:
    """One point in local x/y meters, carried over between pages."""

    x: float
    y: float
    time: datetime


def to_local_xy(
    lat: pd.Series, lon: pd.Series, origin_lat: float, origin_lon: float
) -> tuple[pd.Series, pd.Series]:
    """Convert latitude/longitude in degrees to flat x/y meters around an origin."""
    x = (
        EARTH_RADIUS_M
        * np.radians(lon - origin_lon)
        * math.cos(math.radians(origin_lat))
    )
    y = EARTH_RADIUS_M * np.radians(lat - origin_lat)
    return x, y


def seconds_since(times: pd.Series, start_time: datetime) -> pd.Series:
    """Seconds from `start_time` to each time, as floats."""
    return (times - start_time).dt.total_seconds()


def downsample(page: pd.DataFrame, rows_before_page: int, every_n: int) -> pd.DataFrame:
    """Keep every `every_n`-th row of the run, counted across all pages."""
    # Position in the page of the first row whose global index is divisible by every_n.
    start = -rows_before_page % every_n
    return page.iloc[start::every_n]


def squared_distances(
    qx: float, qy: float, xn: NDArray[np.float64], yn: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Squared distance from Q to every point P in `xn`/`yn`, all at once."""
    return (xn - qx) ** 2 + (yn - qy) ** 2


def heading_at(visited: VisitedPoints, index: int) -> tuple[float, float] | None:
    """The unit direction of travel at a visited point, or None if it's stationary."""
    before = max(index - 1, 0)
    after = min(index + 1, len(visited.x) - 1)
    hx = float(visited.x[after] - visited.x[before])
    hy = float(visited.y[after] - visited.y[before])
    span = math.hypot(hx, hy)
    if span == 0:
        return None
    return hx / span, hy / span


def find_lap_start(
    x: pd.Series,
    y: pd.Series,
    time_s: pd.Series,
    visited: VisitedPoints,
    hitbox_radius_m: float,
    min_revisit_time_s: float,
    min_revisit_distance_m: float,
) -> tuple[int, tuple[float, float]] | None:
    """Find the first spot the car drives over again and its heading, or None."""
    xn = x.to_numpy(dtype=np.float64)
    yn = y.to_numpy(dtype=np.float64)
    tn = time_s.to_numpy(dtype=np.float64)
    if len(xn) == 0:
        return None

    # 1. Distance driven, continuing from the last visited point if there is one.
    has_visited = len(visited.x) > 0
    start_x = visited.x[-1] if has_visited else xn[0]
    start_y = visited.y[-1] if has_visited else yn[0]
    start_distance = visited.distance_m[-1] if has_visited else 0.0
    steps = np.hypot(np.diff(xn, prepend=start_x), np.diff(yn, prepend=start_y))
    distances_m = start_distance + np.cumsum(steps)

    # 2. Extend visited first, so returned indices refer to visited itself.
    first_q = len(visited.x)
    visited.x = np.concatenate((visited.x, xn))
    visited.y = np.concatenate((visited.y, yn))
    visited.time_s = np.concatenate((visited.time_s, tn))
    visited.distance_m = np.concatenate((visited.distance_m, distances_m))

    # 3. Check each of this page's points against the points well before it.
    for q in range(first_q, len(visited.x)):
        time_cutoff_index = np.searchsorted(
            visited.time_s[:q], visited.time_s[q] - min_revisit_time_s, side="right"
        )
        dist_cutoff_index = np.searchsorted(
            visited.distance_m[:q],
            visited.distance_m[q] - min_revisit_distance_m,
            side="right",
        )
        cutoff_index = min(time_cutoff_index, dist_cutoff_index)

        dists_squared = squared_distances(
            visited.x[q],
            visited.y[q],
            visited.x[:cutoff_index],
            visited.y[:cutoff_index],
        )
        candidates_indices = np.flatnonzero(dists_squared <= hitbox_radius_m**2)
        for index in candidates_indices[np.argsort(dists_squared[candidates_indices])]:
            heading = heading_at(visited, int(index))
            if heading is not None:
                return int(index), heading

    return None


def build_gate(
    center_x: float, center_y: float, heading: tuple[float, float], half_width_m: float
) -> Gate:
    """Build the gate through a center point, perpendicular to the heading."""
    nx, ny = -heading[1], heading[0]
    return Gate(
        g1_x=center_x + half_width_m * nx,
        g1_y=center_y + half_width_m * ny,
        g2_x=center_x - half_width_m * nx,
        g2_y=center_y - half_width_m * ny,
    )


def cross_2d(v1_x: float, v1_y: float, v2_x: float, v2_y: float) -> float:
    """The 2D cross product of v1 and v2, positive if v2 points to the left of v1."""
    return v1_x * v2_y - v1_y * v2_x


def is_past_line(
    start_x: float, start_y: float, end_x: float, end_y: float, px: float, py: float
) -> bool:
    """Whether point p is on or left of the line from start to end."""
    return cross_2d(end_x - start_x, end_y - start_y, px - start_x, py - start_y) >= 0


def is_past_gate(px: float, py: float, gate: Gate) -> bool:
    """Whether a point is on or past the gate's line."""
    return is_past_line(gate.g1_x, gate.g1_y, gate.g2_x, gate.g2_y, px, py)


def is_between_gate(
    p1_x: float, p1_y: float, p2_x: float, p2_y: float, gate: Gate
) -> bool:
    """Whether the path from p1 to p2 goes between the gate's two ends."""
    g1_side = is_past_line(p1_x, p1_y, p2_x, p2_y, gate.g1_x, gate.g1_y)
    g2_side = is_past_line(p1_x, p1_y, p2_x, p2_y, gate.g2_x, gate.g2_y)
    return g1_side != g2_side


def crosses_gate(
    p1_x: float, p1_y: float, p2_x: float, p2_y: float, gate: Gate
) -> bool:
    """Whether driving from p1 to the next point p2 passes forward through the gate."""
    return (
        not is_past_gate(p1_x, p1_y, gate)
        and is_past_gate(p2_x, p2_y, gate)
        and is_between_gate(p1_x, p1_y, p2_x, p2_y, gate)
    )


def find_crossings(
    x: pd.Series,
    y: pd.Series,
    times: pd.Series,
    gate: Gate,
    previous: TrackPoint | None,
) -> list[datetime]:
    """Times of every forward pass through the gate in one page."""
    xn, yn, tn = x.tolist(), y.tolist(), times.tolist()
    if previous is not None:
        xn.insert(0, previous.x)
        yn.insert(0, previous.y)
        tn.insert(0, previous.time)

    crossing_times = []
    for b in range(1, len(xn)):
        if crosses_gate(xn[b - 1], yn[b - 1], xn[b], yn[b], gate):
            crossing_times.append(tn[b])
    return crossing_times


def apply_min_lap_time(
    crossing_times: list[datetime],
    last_counted_time: datetime | None,
    min_lap_time_s: float,
) -> list[datetime]:
    """Drop crossings that come too soon after the last counted one."""
    kept: list[datetime] = []
    for crossing in crossing_times:
        if (
            last_counted_time is None
            or (crossing - last_counted_time).total_seconds() >= min_lap_time_s
        ):
            kept.append(crossing)
            last_counted_time = crossing
    return kept


def build_lap_rows(
    run_id: str, lap_id: int, lap_start: datetime, crossing_times: list[datetime]
) -> tuple[pd.DataFrame, int, datetime]:
    """Close one lap per crossing and return the rows and next lap state."""
    rows = []
    for crossing in crossing_times:
        rows.append((run_id, lap_id, lap_start, crossing))
        lap_id += 1
        lap_start = crossing
    columns = ["run_id", "lap_id", "start_time", "end_time"]
    return pd.DataFrame(rows, columns=columns), lap_id, lap_start
