"""Pure geometry helpers for lap detection. See docs/lap_detection.md."""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

# Mean Earth radius, used to turn latitude/longitude angles into meters.
EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class Gate:
    """The start/finish line, as a segment from G1 to G2 in local x/y meters.

    G1 is the gate's left end and G2 its right end, when facing the driving
    direction. This order is what makes the sign of `side_of_gate` mean
    behind (negative) or past (zero or positive).
    """

    g1_x: float
    g1_y: float
    g2_x: float
    g2_y: float


@dataclass
class RevisitMemory:
    """Every sampled Pass 1 point that wasn't a revisit, in time order.

    The lists are parallel: index i of each list describes the same point.
    `time_s` is seconds since the run's first point, and `distance_m` is the
    total distance driven up to that point.
    """

    x: list[float] = field(default_factory=list)
    y: list[float] = field(default_factory=list)
    time_s: list[float] = field(default_factory=list)
    distance_m: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class TrackPoint:
    """One point in local x/y meters. Pass 2 carries the last point of each
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
    both passes must use the same origin.

    Args:
        lat: Latitude of each point, in degrees.
        lon: Longitude of each point, in degrees.
        origin_lat: Latitude of the origin, in degrees.
        origin_lon: Longitude of the origin, in degrees.

    Returns:
        (x, y) in meters, with the same index as `lat` and `lon`.

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


def seconds_since(times: pd.Series, start_time: datetime) -> pd.Series:
    """Seconds from `start_time` to each time, as floats.

    Args:
        times: Timestamps of the points.
        start_time: The run's first time.

    Returns:
        `(times - start_time)` in seconds, with the same index as `times`.

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


def downsample(
    page: pd.DataFrame, first_global_index: int, every_n: int
) -> pd.DataFrame:
    """Keep every `every_n`-th row of the run, counted across all pages.

    A row's global index is `first_global_index` plus its position in the page
    (0, 1, 2, ...). The row is kept when `global_index % every_n == 0`. Counting
    across the run rather than per page means the spacing stays even over page
    boundaries. With `every_n = 1` every row is kept.

    Args:
        page: One page of the run, in time order.
        first_global_index: Global index of the page's first row (the number
            of rows in all earlier pages).
        every_n: Keep one row in every `every_n`.

    Returns:
        The kept rows, in their original order.

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


def in_hitbox(qx: float, qy: float, px: float, py: float, radius_m: float) -> bool:
    """Whether Q is inside the circular hitbox of radius `radius_m` around P.

    Compares squared distances, so no square root is needed:

        (qx - px)^2 + (qy - py)^2 <= radius_m^2

    Example: P=(10, 10), radius 3. Q=(12, 11) gives 4 + 1 = 5 <= 9, so it's
    inside. Q=(13, 13) gives 9 + 9 = 18 > 9, so it's outside.

    Args:
        qx: Q's x, in meters.
        qy: Q's y, in meters.
        px: P's x, in meters.
        py: P's y, in meters.
        radius_m: Hitbox radius, in meters.

    Returns:
        True if Q is inside or on the edge of P's hitbox.

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


def heading_at(
    memory: RevisitMemory, index: int, min_span_m: float
) -> tuple[float, float] | None:
    """The unit direction of travel at a remembered point, from its neighbors.

    `before` is the remembered point at `index - 1`, or the point itself if
    `index` is 0. `after` is the point at `index + 1`, or the point itself if
    it's the last one. Then:

        h = after - before
        heading = h / |h|

    If `|h| < min_span_m`, the car was essentially standing still at the
    point (e.g. parked on the line before driving), so there's no usable
    heading. Example: before=(-1, 0), after=(1, 0) gives h=(2, 0), |h|=2, and
    heading (1, 0).

    Args:
        memory: The remembered Pass 1 points.
        index: Index of the point in `memory`.
        min_span_m: Smallest `|h|` that gives a valid heading, in meters.

    Returns:
        The unit heading (hx, hy), or None if the span is too small.

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


def find_revisit(
    x: pd.Series,
    y: pd.Series,
    time_s: pd.Series,
    memory: RevisitMemory,
    hitbox_radius_m: float,
    min_revisit_time_s: float,
    min_revisit_distance_m: float,
    min_heading_span_m: float,
) -> tuple[int, tuple[float, float]] | None:
    """Look for the first place the car drives over a spot it already passed.

    Walks this page's sampled points Q in order. For each Q:

    1. Work out Q's distance driven: the last `distance_m` in memory plus the
       straight-line distance from the previous sampled point (the last one
       in memory), `sqrt((x - x_prev)^2 + (y - y_prev)^2)`. If memory is
       empty, it's 0. Example: (0,0), (3,4), (6,8) give 0, 5, 10.
    2. Find every remembered point P that is a candidate, meaning all of:
       - `in_hitbox(Q, P, hitbox_radius_m)`,
       - `time_s[Q] - time_s[P] >= min_revisit_time_s`,
       - `distance_m[Q] - distance_m[P] >= min_revisit_distance_m`.
    3. Try the candidates closest-first (smallest squared distance to Q). The
       first one where `heading_at(memory, P, min_heading_span_m)` isn't None
       is the gate center: return its index and heading right away.
    4. Otherwise append Q (x, y, time_s, distance_m) to memory and move on.

    The memory is updated in place, so it carries over to the next page.

    Args:
        x: x of this page's sampled points, in meters.
        y: y of this page's sampled points, in meters.
        time_s: Seconds since the run's first point, for each sampled point.
        memory: Every earlier sampled point that wasn't a revisit. Updated in place.
        hitbox_radius_m: Radius of each remembered point's hitbox.
        min_revisit_time_s: Minimum time between P and Q for a hit to count.
        min_revisit_distance_m: Minimum distance driven between P and Q for a
            hit to count.
        min_heading_span_m: Passed to `heading_at`.

    Returns:
        (memory index of the gate center, unit heading at it) for the first
        valid revisit, or None if this page has none.

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


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

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


def cross_2d(ux: float, uy: float, vx: float, vy: float) -> float:
    """The 2D cross product of arrows u and v.

        cross(u, v) = ux*vy - uy*vx

    Positive if v points to the left of u, negative if it points to the
    right, and zero if they lie along the same line. Example: u=(1, 0),
    v=(0, 1) gives 1 (v is to the left).

    Args:
        ux: u's x.
        uy: u's y.
        vx: v's x.
        vy: v's y.

    Returns:
        cross(u, v).

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


def side_of_gate(x: float, y: float, gate: Gate) -> float:
    """Which side of the gate's line a point P is on.

        side(P) = cross(G2 - G1, P - G1)

    Negative means P is behind the line (not reached yet). Zero or positive
    means it's on or past the line.

    Args:
        x: P's x, in meters.
        y: P's y, in meters.
        gate: The gate.

    Returns:
        side(P).

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


def crosses_gate(ax: float, ay: float, bx: float, by: float, gate: Gate) -> bool:
    """Whether driving from A to B is a forward pass through the gate.

    Both of these must hold:

    1. Forward across the line: `side(A) < 0` and `side(B) >= 0`, using
       `side_of_gate`. Driving backwards through it doesn't count, and a
       point exactly on the line counts as past, so it's only counted once.
    2. Inside the gate: G1 and G2 are on opposite sides of the line through
       A and B. With

           d1 = cross(B - A, G1 - A)
           d2 = cross(B - A, G2 - A)

       it counts if `d1 * d2 <= 0`. This rejects crossings of the gate line's
       extension elsewhere on the track. Touching a gate end exactly counts.

    Args:
        ax: A's x, in meters.
        ay: A's y, in meters.
        bx: B's x, in meters.
        by: B's y, in meters.
        gate: The gate.

    Returns:
        True if A -> B counts as a crossing.

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


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

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


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

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


def build_lap_rows(
    run_id: str, lap_id: int, lap_start: datetime, crossing_times: list[datetime]
) -> tuple[pd.DataFrame, int, datetime]:
    """Close one lap per crossing.

    For each crossing in order, emits the row (run_id, lap_id, lap_start,
    crossing), then adds 1 to lap_id and sets lap_start to the crossing. The
    lap that is still open after the last crossing isn't emitted; the step
    writes it once the run ends.

    Args:
        run_id: The run's id.
        lap_id: Id of the lap currently open.
        lap_start: Start time of the lap currently open.
        crossing_times: Counted crossings, in order.

    Returns:
        (rows with columns run_id, lap_id, start_time, end_time, which is
        empty if there are no crossings; the next lap_id; the new lap_start).

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError


def make_lap_row(
    run_id: str, lap_id: int, start_time: datetime, end_time: datetime
) -> pd.DataFrame:
    """A one-row DataFrame for a single lap.

    Args:
        run_id: The run's id.
        lap_id: The lap's number within the run.
        start_time: When the lap started.
        end_time: When the lap ended.

    Returns:
        One row with columns run_id, lap_id, start_time, end_time.

    Raises:
        NotImplementedError: Not implemented yet.
    """
    raise NotImplementedError
