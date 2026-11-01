"""Pure geometry helpers for lap detection. See docs/lap_detection.md."""

import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from orion_pipeline.steps.lap_step.lap_constants import EARTH_RADIUS_M


@dataclass(frozen=True)
class Gate:
    """The start/finish line, as a segment from G1 to G2 in local x/y meters.

    G1 is the gate's left end and G2 its right end, when facing the driving
    direction. This order is what makes `is_past_gate` mean ahead of the
    gate rather than behind it.
    """

    g1_x: float
    g1_y: float
    g2_x: float
    g2_y: float


@dataclass
class VisitedPoints:
    """Every point sampled while searching for the gate, in time order.

    These are the candidates a later point can revisit, not revisits
    themselves. The arrays are parallel: index i of each array is the same
    point. `time_s` is seconds since the run's first point, and `distance_m`
    is the total distance driven up to that point.
    """

    x: NDArray[np.float64] = field(default_factory=lambda: np.empty(0))
    y: NDArray[np.float64] = field(default_factory=lambda: np.empty(0))
    time_s: NDArray[np.float64] = field(default_factory=lambda: np.empty(0))
    distance_m: NDArray[np.float64] = field(default_factory=lambda: np.empty(0))


@dataclass(frozen=True)
class TrackPoint:
    """One point in local x/y meters. Counting laps carries the last point of each
    page over to the next page, so a crossing on a page boundary isn't missed."""

    x: float
    y: float
    time: datetime


def to_local_xy(
    lat: pd.Series, lon: pd.Series, origin_lat: float, origin_lon: float
) -> tuple[pd.Series, pd.Series]:
    """Convert latitude/longitude in degrees to flat x/y meters around an origin.

    Uses an equirectangular projection, which is accurate enough over an area
    the size of a track:

        x = EARTH_RADIUS_M * radians(lon - origin_lon) * cos(radians(origin_lat))
        y = EARTH_RADIUS_M * radians(lat - origin_lat)

    x points east and y points north. The origin is the run's first point, and
    both modes must use the same origin.

    Args:
        lat: Latitude of each point, in degrees.
        lon: Longitude of each point, in degrees.
        origin_lat: Latitude of the origin, in degrees.
        origin_lon: Longitude of the origin, in degrees.

    Returns:
        (x, y) in meters, with the same index as `lat` and `lon`.
    """
    x = (
        EARTH_RADIUS_M
        * np.radians(lon - origin_lon)
        * math.cos(math.radians(origin_lat))
    )
    y = EARTH_RADIUS_M * np.radians(lat - origin_lat)
    return x, y


def seconds_since(times: pd.Series, start_time: datetime) -> pd.Series:
    """Seconds from `start_time` to each time, as floats.

    Args:
        times: Timestamps of the points.
        start_time: The run's first time.

    Returns:
        `(times - start_time)` in seconds, with the same index as `times`.
    """
    return (times - start_time).dt.total_seconds()


def downsample(page: pd.DataFrame, rows_before_page: int, every_n: int) -> pd.DataFrame:
    """Keep every `every_n`-th row of the run, counted across all pages.

    A row's global index is `rows_before_page` plus its position in the page
    (0, 1, 2, ...). The row is kept when `global_index % every_n == 0`. Counting
    across the run rather than per page means the spacing stays even over page
    boundaries. With `every_n = 1` every row is kept.

    Args:
        page: One page of the run, in time order.
        rows_before_page: Global index of the page's first row (the number
            of rows in all earlier pages).
        every_n: Keep one row in every `every_n`.

    Returns:
        The kept rows, in their original order.
    """
    # Position in the page of the first row whose global index is divisible by every_n.
    start = -rows_before_page % every_n
    return page.iloc[start::every_n]


def squared_distances(
    qx: float, qy: float, xn: NDArray[np.float64], yn: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Squared distance from Q to every point P in `xn`/`yn`, all at once.

        (xn - qx)^2 + (yn - qy)^2

    Q is inside P's hitbox when this is `<= HITBOX_RADIUS_M^2`. Comparing
    squared distances means no square root is needed.

    Example: P=(10, 10), radius 3. Q=(12, 11) gives 4 + 1 = 5 <= 9, so it's
    inside. Q=(13, 13) gives 9 + 9 = 18 > 9, so it's outside.

    Args:
        qx: Q's x, in meters.
        qy: Q's y, in meters.
        xn: x of each point P, in meters.
        yn: y of each point P, in meters.

    Returns:
        The squared distance to each P, in square meters, in the same order
        as `xn` and `yn`.
    """
    return (xn - qx) ** 2 + (yn - qy) ** 2


def heading_at(visited: VisitedPoints, index: int) -> tuple[float, float] | None:
    """The unit direction of travel at a visited point, from its neighbors.

    `before` is the visited point at `index - 1`, or the point itself if
    `index` is 0. `after` is the point at `index + 1`, or the point itself if
    it's the last one. Then:

        h = after - before
        heading = h / |h|

    If `|h|` is 0, `before` and `after` are at the same position (e.g.
    repeated GPS fixes while parked), so there's no direction to divide out.
    Example: before=(-1, 0), after=(1, 0) gives h=(2, 0), |h|=2, and
    heading (1, 0).

    Args:
        visited: The visited points.
        index: Index of the point in `visited`.

    Returns:
        The unit heading (hx, hy), or None if `|h|` is 0.
    """
    before = max(index - 1, 0)
    after = min(index + 1, len(visited.x) - 1)
    hx = float(visited.x[after] - visited.x[before])
    hy = float(visited.y[after] - visited.y[before])
    span = math.hypot(hx, hy)
    if span == 0:
        return None
    return hx / span, hy / span


def find_revisit(
    x: pd.Series,
    y: pd.Series,
    time_s: pd.Series,
    visited: VisitedPoints,
    hitbox_radius_m: float,
    min_revisit_time_s: float,
    min_revisit_distance_m: float,
) -> tuple[int, tuple[float, float]] | None:
    """Look for the first place the car drives over a spot it already passed.

    Converts `x`, `y`, and `time_s` with `.to_numpy()`, then:

    1. Distance driven for this page, all at once. Step lengths are
       `sqrt(dx^2 + dy^2)` between consecutive points, and the page's first
       step is measured from the last point in `visited`, if there is one.
       `distance_m` is the running total (cumsum) of the steps, starting from
       the last `distance_m` in `visited`, or 0 if `visited` is empty.
       Example: (0,0), (3,4), (6,8) give 0, 5, 10.
    2. Extend `visited` once, in place: concatenate this page's x, y, time_s,
       and distance_m onto its four arrays. This happens first, so any index
       returned below refers to `visited` itself.
    3. For each of this page's points Q, at position q in `visited`, in time
       order:
       1. Cutoff. `time_s` and `distance_m` only ever increase, so every
          point before some position is at least `min_revisit_time_s` and
          `min_revisit_distance_m` of driving earlier than Q, and every point
          after it isn't:
              time_cut = searchsorted(time_s[:q],
                                      time_s[q] - min_revisit_time_s,
                                      side="right")
              dist_cut = (the same, with distance_m and min_revisit_distance_m)
              cutoff = min(time_cut, dist_cut)
          Only points before `cutoff` can be candidates.
       2. Hitbox test. `d2 = squared_distances(Q, x[:cutoff], y[:cutoff])`.
          The candidates are the indices where `d2 <= hitbox_radius_m^2`.
       3. Closest first. Try the candidates sorted by `d2`, smallest first.
          The first one where `heading_at(visited, index)` isn't None is the
          gate center: return `(index, heading)` right away, without checking
          the rest of the page. If every candidate's heading is None, move on
          to the next Q.
    4. Return None if no point on this page found a revisit.

    `visited` keeps the whole page either way, so it carries over to the next
    page.

    Args:
        x: x of this page's sampled points, in meters.
        y: y of this page's sampled points, in meters.
        time_s: Seconds since the run's first point, for each sampled point.
        visited: Every earlier sampled point. Extended in place with this page.
        hitbox_radius_m: Radius of each visited point's hitbox.
        min_revisit_time_s: Minimum time between P and Q for a hit to count.
        min_revisit_distance_m: Minimum distance driven between P and Q for a
            hit to count.

    Returns:
        (index in `visited` of the gate center, unit heading at it) for the
        first valid revisit, or None if this page has none.
    """
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
    """Build the gate through a center point, perpendicular to the heading.

    With center C, unit heading ĥ, and half width w:

        n̂  = (-hy, hx)    # the heading rotated 90° to the left
        G1 = C + w*n̂      # left end, facing the driving direction
        G2 = C - w*n̂      # right end

    Example: C=(0, 0), heading (1, 0), w=5 gives n̂=(0, 1), G1=(0, 5), and
    G2=(0, -5).

    Args:
        center_x: x of the gate center C, in meters.
        center_y: y of the gate center C, in meters.
        heading: Unit direction of travel at C, (hx, hy).
        half_width_m: How far the gate reaches on each side of C.

    Returns:
        The gate.
    """
    nx, ny = -heading[1], heading[0]
    return Gate(
        g1_x=center_x + half_width_m * nx,
        g1_y=center_y + half_width_m * ny,
        g2_x=center_x - half_width_m * nx,
        g2_y=center_y - half_width_m * ny,
    )


def cross_2d(v1_x: float, v1_y: float, v2_x: float, v2_y: float) -> float:
    """The 2D cross product of vectors v1 and v2.

        v1_x * v2_y - v1_y * v2_x

    Positive if v2 points to the left of v1, negative if it points to the
    right, and zero if they point along the same line. (Right-hand rule:
    fingers along v1, curl toward v2; thumb up is positive.)

    Args:
        v1_x: x of v1.
        v1_y: y of v1.
        v2_x: x of v2.
        v2_y: y of v2.

    Returns:
        The cross product.
    """
    return v1_x * v2_y - v1_y * v2_x


def is_past_line(
    start_x: float, start_y: float, end_x: float, end_y: float, px: float, py: float
) -> bool:
    """Whether point p is past the line from start to end, or on it.

    "Past" means on the left side when facing from start toward end. Uses the
    cross product of (end - start) and (p - start), which is positive on the
    left, negative on the right, and zero on the line.

    Args:
        start_x: x of the line's start, in meters.
        start_y: y of the line's start, in meters.
        end_x: x of the line's end, in meters.
        end_y: y of the line's end, in meters.
        px: x of the point, in meters.
        py: y of the point, in meters.

    Returns:
        True if p is past the line or exactly on it.
    """
    return cross_2d(end_x - start_x, end_y - start_y, px - start_x, py - start_y) >= 0


def is_past_gate(px: float, py: float, gate: Gate) -> bool:
    """Whether a point is on or past the gate's line.

    G1 is the gate's left end and G2 its right end, facing the driving
    direction, so past the line G1 -> G2 is past the gate.

    Args:
        px: x of the point, in meters.
        py: y of the point, in meters.
        gate: The gate.

    Returns:
        True if the point is on or past the gate's line.
    """
    return is_past_line(gate.g1_x, gate.g1_y, gate.g2_x, gate.g2_y, px, py)


def is_between_gate(
    p1_x: float, p1_y: float, p2_x: float, p2_y: float, gate: Gate
) -> bool:
    """Whether the path from p1 to p2 goes between the gate's two ends.

    True when exactly one of G1 and G2 is past the path's line, meaning the
    ends are on different sides of the path. This rejects crossing the gate's
    line extended, elsewhere on the track.

    Args:
        p1_x: x of the earlier point, in meters.
        p1_y: y of the earlier point, in meters.
        p2_x: x of the next point, in meters.
        p2_y: y of the next point, in meters.
        gate: The gate.

    Returns:
        True if the path goes between G1 and G2.
    """
    g1_side = is_past_line(p1_x, p1_y, p2_x, p2_y, gate.g1_x, gate.g1_y)
    g2_side = is_past_line(p1_x, p1_y, p2_x, p2_y, gate.g2_x, gate.g2_y)
    return g1_side != g2_side


def crosses_gate(
    p1_x: float, p1_y: float, p2_x: float, p2_y: float, gate: Gate
) -> bool:
    """Whether driving from p1 to the next point p2 is a forward pass through the gate.

    p1 must be behind the gate, p2 on or past it, and the path between them
    must go between the gate's two ends.

    Args:
        p1_x: x of the earlier point, in meters.
        p1_y: y of the earlier point, in meters.
        p2_x: x of the next point, in meters.
        p2_y: y of the next point, in meters.
        gate: The gate.

    Returns:
        True if p1 -> p2 counts as a crossing.
    """
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
    """Times of every forward pass through the gate in one page.

    Checks every consecutive pair of points (A, B) with `crosses_gate`. If
    `previous` is given (the last point of the previous page), the pair
    (previous, first point of this page) is checked first. For each pair that
    crosses, the time of B (the first point past the line) is recorded. The
    minimum lap time is NOT applied here; see `apply_min_lap_time`.

    Args:
        x: x of every point in the page, in meters, in time order.
        y: y of every point in the page, in meters.
        times: Time of every point in the page.
        gate: The gate.
        previous: Last point of the previous page, or None on the first page.

    Returns:
        t(B) for each crossing, in time order.
    """
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
    """Drop crossings that come too soon after the last counted one.

    Goes through the crossings in order. A crossing is kept if there's no
    counted crossing yet, or if it's at least `min_lap_time_s` seconds after
    the last counted one. Each kept crossing becomes the new last counted
    one, and rejected ones don't. The first crossing of the run is always
    kept. This stops GPS jitter at the line from creating extra laps.

    Args:
        crossing_times: Crossing times from `find_crossings`, in order.
        last_counted_time: The last counted crossing from earlier pages, or None.
        min_lap_time_s: Minimum time between two counted crossings.

    Returns:
        The crossings that count, in order.
    """
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
    """Close one lap per crossing.

    For each crossing in order, emits the row (run_id, lap_id, lap_start,
    crossing), then adds 1 to lap_id and sets lap_start to the crossing. To
    close the final lap, the step passes the run's end time as the last
    crossing.

    Args:
        run_id: The run's id.
        lap_id: Id of the lap currently open.
        lap_start: Start time of the lap currently open.
        crossing_times: Counted crossings, in order.

    Returns:
        (rows with columns run_id, lap_id, start_time, end_time, which is
        empty if there are no crossings; the next lap_id; the new lap_start).
    """
    rows = []
    for crossing in crossing_times:
        rows.append((run_id, lap_id, lap_start, crossing))
        lap_id += 1
        lap_start = crossing
    columns = ["run_id", "lap_id", "start_time", "end_time"]
    return pd.DataFrame(rows, columns=columns), lap_id, lap_start
