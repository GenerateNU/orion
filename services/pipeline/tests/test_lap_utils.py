from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.steps.lap_step.lap_constants import (
    EARTH_RADIUS_M,
    GATE_HALF_WIDTH_M,
    GATE_SEARCH_SAMPLE_EVERY,
    HITBOX_RADIUS_M,
    MIN_LAP_TIME_S,
    MIN_REVISIT_DISTANCE_M,
    MIN_REVISIT_TIME_S,
)
from orion_pipeline.steps.lap_step.lap_utils import (
    Gate,
    TrackPoint,
    VisitedPoints,
    apply_min_lap_time,
    build_gate,
    build_lap_rows,
    cross_2d,
    crosses_gate,
    downsample,
    find_crossings,
    find_revisit,
    heading_at,
    is_between_gate,
    is_past_gate,
    is_past_line,
    seconds_since,
    squared_distances,
    to_local_xy,
)

START = datetime(2026, 1, 1, 12, 0, 0)
# Facing +x through the origin: G1 is the left end (0, 5), G2 the right end (0, -5).
GATE = Gate(g1_x=0.0, g1_y=5.0, g2_x=0.0, g2_y=-5.0)


def at(seconds: float) -> datetime:
    return START + timedelta(seconds=seconds)


def visited_points(xn, yn) -> VisitedPoints:
    return VisitedPoints(x=np.array(xn, dtype=float), y=np.array(yn, dtype=float))


def test_to_local_xy_origin_is_zero():
    x, y = to_local_xy(pd.Series([42.0]), pd.Series([-71.0]), 42.0, -71.0)
    assert x.iloc[0] == pytest.approx(0.0)
    assert y.iloc[0] == pytest.approx(0.0)


def test_to_local_xy_north_and_east():
    one_degree_m = EARTH_RADIUS_M * np.pi / 180
    x, y = to_local_xy(pd.Series([1.0, 0.0]), pd.Series([0.0, 1.0]), 0.0, 0.0)
    assert x.tolist() == pytest.approx([0.0, one_degree_m])
    assert y.tolist() == pytest.approx([one_degree_m, 0.0])


def test_to_local_xy_shrinks_east_with_latitude():
    x, _ = to_local_xy(pd.Series([60.0]), pd.Series([1.0]), 60.0, 0.0)
    assert x.iloc[0] == pytest.approx(EARTH_RADIUS_M * np.pi / 180 * 0.5)


def test_seconds_since():
    times = pd.Series([START, at(1.5), at(10)])
    assert seconds_since(times, START).tolist() == [0.0, 1.5, 10.0]


def test_downsample_counts_across_pages():
    page = pd.DataFrame({"i": range(7, 17)})
    # Global indices 7..16; the multiples of 5 are 10 and 15.
    assert downsample(page, 7, 5)["i"].tolist() == [10, 15]


def test_downsample_every_row():
    page = pd.DataFrame({"i": range(4)})
    assert downsample(page, 3, 1)["i"].tolist() == [0, 1, 2, 3]


def test_squared_distances():
    d2 = squared_distances(10.0, 10.0, np.array([12.0, 13.0]), np.array([11.0, 13.0]))
    assert d2.tolist() == [5.0, 18.0]


def test_heading_at_uses_neighbors():
    visited = visited_points([-1, 0, 1], [0, 0, 0])
    assert heading_at(visited, 1) == pytest.approx((1.0, 0.0))


def test_heading_at_ends_use_the_point_itself():
    visited = visited_points([0, 0, 0], [0, 3, 4])
    assert heading_at(visited, 0) == pytest.approx((0.0, 1.0))
    assert heading_at(visited, 2) == pytest.approx((0.0, 1.0))


def test_heading_at_is_unit_length_even_when_slow():
    visited = visited_points([0, 0.01, 0.02], [0, 0, 0])
    assert heading_at(visited, 1) == pytest.approx((1.0, 0.0))


def test_heading_at_standing_still_is_none():
    visited = visited_points([0, 0, 0], [0, 0, 0])
    assert heading_at(visited, 1) is None


def test_build_gate_is_perpendicular_to_heading():
    assert build_gate(0.0, 0.0, (1.0, 0.0), 5.0) == GATE


def test_cross_2d_sign():
    assert cross_2d(1, 0, 0, 1) == 1
    assert cross_2d(1, 0, 0, -1) == -1
    assert cross_2d(1, 0, 2, 0) == 0


def test_is_past_line_is_left_of_start_to_end():
    # Facing +x from (0, 0) to (1, 0), +y is on the left.
    assert is_past_line(0, 0, 1, 0, 5, 1) is True
    assert is_past_line(0, 0, 1, 0, 5, 0) is True
    assert is_past_line(0, 0, 1, 0, 5, -1) is False


def test_is_past_gate():
    assert is_past_gate(-1, 0, GATE) is False
    assert is_past_gate(0, 0, GATE) is True
    assert is_past_gate(1, 0, GATE) is True


def test_is_between_gate():
    assert is_between_gate(-1, 0, 1, 0, GATE) is True
    assert is_between_gate(-1, 20, 1, 20, GATE) is False
    assert is_between_gate(-1, -20, 1, -20, GATE) is False


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ((-1, 0), (1, 0), True),  # forward through the middle
        ((-1, 0), (0, 0), True),  # landing exactly on the line counts
        ((0, 0), (1, 0), False),  # starting on the line was already counted
        ((1, 0), (-1, 0), False),  # backwards
        ((-1, 20), (1, 20), False),  # the line's extension, outside the gate
        ((-1, 5), (1, 5), True),  # touching a gate end
        ((-2, -1), (-1, 1), False),  # never reaches the line
    ],
)
def test_crosses_gate(a, b, expected):
    (ax, ay), (bx, by) = a, b
    assert crosses_gate(ax, ay, bx, by, GATE) is expected


def test_find_crossings_records_time_of_first_point_past():
    x = pd.Series([-2.0, -1.0, 1.0, 2.0])
    y = pd.Series([0.0, 0.0, 0.0, 0.0])
    times = pd.Series([at(0), at(1), at(2), at(3)])
    assert find_crossings(x, y, times, GATE, None) == [at(2)]


def test_find_crossings_on_a_page_boundary():
    previous = TrackPoint(x=-1.0, y=0.0, time=at(0))
    x, y, times = pd.Series([1.0]), pd.Series([0.0]), pd.Series([at(1)])
    assert find_crossings(x, y, times, GATE, previous) == [at(1)]
    assert find_crossings(x, y, times, GATE, None) == []


def test_apply_min_lap_time_drops_jitter():
    crossings = [at(0), at(2), at(10), at(15), at(21)]
    assert apply_min_lap_time(crossings, None, 10) == [at(0), at(10), at(21)]


def test_apply_min_lap_time_uses_earlier_pages():
    assert apply_min_lap_time([at(5), at(12)], at(0), 10) == [at(12)]


def test_build_lap_rows_chains_laps():
    rows, next_id, next_start = build_lap_rows("run", 3, at(0), [at(30), at(65)])
    assert rows.to_dict("records") == [
        {"run_id": "run", "lap_id": 3, "start_time": at(0), "end_time": at(30)},
        {"run_id": "run", "lap_id": 4, "start_time": at(30), "end_time": at(65)},
    ]
    assert (next_id, next_start) == (5, at(65))


def test_build_lap_rows_without_crossings():
    rows, next_id, next_start = build_lap_rows("run", 1, at(0), [])
    assert rows.empty
    assert list(rows.columns) == ["run_id", "lap_id", "start_time", "end_time"]
    assert (next_id, next_start) == (1, at(0))


def search(visited, xn, yn, tn, radius, min_time, min_distance):
    """find_revisit on plain lists, with the thresholds in a readable order."""
    return find_revisit(
        pd.Series(xn, dtype=float),
        pd.Series(yn, dtype=float),
        pd.Series(tn, dtype=float),
        visited,
        radius,
        min_time,
        min_distance,
    )


def test_find_revisit_finds_return_to_start():
    # A 10 m x 10 m square driven 1 m per second, ending back at the start.
    xn = [*range(10), *[10] * 10, *range(10, 0, -1), *[0] * 11]
    yn = [*[0] * 10, *range(10), *[10] * 10, *range(10, -1, -1)]
    visited = VisitedPoints()
    revisit = search(visited, xn, yn, range(len(xn)), 0.5, 5, 30)

    assert revisit is not None
    index, heading = revisit
    assert index == 0
    assert heading == pytest.approx((1.0, 0.0))
    assert visited.distance_m[-1] == pytest.approx(40.0)


def test_find_revisit_needs_enough_distance_driven():
    # Standing still: every point is inside every hitbox, but nothing is driven.
    visited = VisitedPoints()
    assert search(visited, [0] * 20, [0] * 20, range(20), 3, 5, 50) is None


def test_find_revisit_carries_visited_across_pages():
    visited = VisitedPoints()
    assert search(visited, [0, 10, 20], [0, 0, 0], [0, 1, 2], 3, 1, 20) is None
    assert visited.distance_m.tolist() == [0, 10, 20]

    # The second page continues the distance and comes back to the start.
    revisit = search(visited, [10, 0.5], [5, 0], [3, 4], 3, 1, 20)
    assert revisit is not None
    assert revisit[0] == 0
    assert len(visited.x) == 5


def test_find_revisit_picks_the_closest_candidate():
    # Two points 2 m apart, then a loop that comes back next to the second one.
    xn = [0, 2, 10, 20, 10, 2.5]
    yn = [0, 0, 0, 10, 20, 0]
    revisit = search(VisitedPoints(), xn, yn, range(6), 3, 1, 20)
    # Both (0, 0) and (2, 0) are inside the hitbox, but (2, 0) is closer.
    assert revisit is not None
    index, heading = revisit
    assert index == 1
    assert heading == pytest.approx((1.0, 0.0))


def test_find_revisit_skips_candidates_without_heading():
    # Parked at the start (points 0-2), then a loop back to (0, 0).
    xn = [0, 0, 0, 10, 20, 10, 0]
    yn = [0, 0, 0, 0, 10, 20, 0.5]
    revisit = search(VisitedPoints(), xn, yn, range(7), 3, 1, 20)
    # Points 0-2 are equally close, but only point 2 has a nonzero heading span.
    assert revisit is not None
    index, heading = revisit
    assert index == 2
    assert heading == pytest.approx((1.0, 0.0))


def test_find_revisit_empty_page_leaves_visited_alone():
    visited = VisitedPoints()
    assert search(visited, [], [], [], 3, 1, 20) is None
    assert len(visited.x) == 0


# The tests below drive realistic tracks through the gate search the way LapStep
# does (downsample, find_revisit with the real thresholds, build_gate), and check
# where the gate ends up.

STRAIGHT_M = 100.0
TURN_RADIUS_M = 30.0
PERIMETER_M = 2 * STRAIGHT_M + 2 * np.pi * TURN_RADIUS_M


def oval(loops: float, start_m: float = 50.0) -> tuple[np.ndarray, np.ndarray]:
    """x, y of an oval driven counterclockwise at 1 m per point (10 m/s at 10 Hz).

    The bottom straight runs from (-50, 0) to (50, 0) heading +x, then a turn
    around (50, 30), the top straight back at y = 60, and a turn around (-50, 30).
    `start_m` is how far along the bottom straight's start the car begins, so
    the default starts at (0, 0).
    """
    half_turn = np.pi * TURN_RADIUS_M
    s = (start_m + np.arange(0, loops * PERIMETER_M)) % PERIMETER_M
    x, y = np.empty_like(s), np.empty_like(s)

    bottom = s < STRAIGHT_M
    x[bottom], y[bottom] = s[bottom] - STRAIGHT_M / 2, 0.0
    right = (s >= STRAIGHT_M) & (s < STRAIGHT_M + half_turn)
    phi = (s[right] - STRAIGHT_M) / TURN_RADIUS_M
    x[right] = STRAIGHT_M / 2 + TURN_RADIUS_M * np.sin(phi)
    y[right] = TURN_RADIUS_M * (1 - np.cos(phi))
    top = (s >= STRAIGHT_M + half_turn) & (s < 2 * STRAIGHT_M + half_turn)
    x[top] = STRAIGHT_M / 2 - (s[top] - STRAIGHT_M - half_turn)
    y[top] = 2 * TURN_RADIUS_M
    left = s >= 2 * STRAIGHT_M + half_turn
    phi = (s[left] - 2 * STRAIGHT_M - half_turn) / TURN_RADIUS_M
    x[left] = -STRAIGHT_M / 2 - TURN_RADIUS_M * np.sin(phi)
    y[left] = TURN_RADIUS_M * (1 + np.cos(phi))
    return x, y


def with_noise(x: np.ndarray, y: np.ndarray, sigma_m: float = 0.5):
    """The path with seeded Gaussian GPS noise added."""
    rng = np.random.default_rng(0)
    return x + rng.normal(0, sigma_m, len(x)), y + rng.normal(0, sigma_m, len(y))


def with_pit_lane(x: np.ndarray, y: np.ndarray):
    """The path, preceded by 60 m of pit lane joining the oval at (-50, 0)."""
    pit_x = np.arange(-110.0, -50.0)
    return np.r_[pit_x, x], np.r_[np.zeros_like(pit_x), y]


def gate_search(x: np.ndarray, y: np.ndarray):
    """(gate center, heading, gate) from a 10 Hz path, or None with no revisit."""
    sampled = slice(None, None, GATE_SEARCH_SAMPLE_EVERY)
    time_s = np.arange(len(x)) / 10
    visited = VisitedPoints()
    revisit = find_revisit(
        pd.Series(x[sampled]),
        pd.Series(y[sampled]),
        pd.Series(time_s[sampled]),
        visited,
        HITBOX_RADIUS_M,
        MIN_REVISIT_TIME_S,
        MIN_REVISIT_DISTANCE_M,
    )
    if revisit is None:
        return None
    index, heading = revisit
    center = (float(visited.x[index]), float(visited.y[index]))
    return center, heading, build_gate(*center, heading, GATE_HALF_WIDTH_M)


def angle_between_deg(a, b) -> float:
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b), -1.0, 1.0))))


def assert_gate_across(gate: Gate, center, heading) -> None:
    """The gate is centered on `center`, perpendicular to `heading`, full width."""
    gx, gy = gate.g2_x - gate.g1_x, gate.g2_y - gate.g1_y
    assert ((gate.g1_x + gate.g2_x) / 2, (gate.g1_y + gate.g2_y) / 2) == pytest.approx(
        center
    )
    assert np.hypot(gx, gy) == pytest.approx(2 * GATE_HALF_WIDTH_M)
    assert np.dot((gx, gy), heading) == pytest.approx(0.0, abs=1e-9)
    # G1 is on the left when facing the driving direction.
    assert cross_2d(heading[0], heading[1], -gx, -gy) > 0


def test_oval_gate_is_across_the_start_straight():
    found = gate_search(*oval(1.5))
    assert found is not None
    center, heading, gate = found
    assert center == pytest.approx((0.0, 0.0))
    assert heading == pytest.approx((1.0, 0.0))
    assert gate == GATE


def test_no_revisit_before_the_loop_is_closed():
    assert gate_search(*oval(0.9)) is None


def test_gate_started_mid_turn_follows_the_turn():
    # 20 m into the first turn, at (50 + 30 sin(phi), 30 (1 - cos(phi))).
    phi = 20 / TURN_RADIUS_M
    start = (50 + TURN_RADIUS_M * np.sin(phi), TURN_RADIUS_M * (1 - np.cos(phi)))
    found = gate_search(*oval(1.5, start_m=STRAIGHT_M + 20))
    assert found is not None
    center, heading, gate = found
    assert center == pytest.approx(start)
    assert_gate_across(gate, center, heading)
    # Heading comes from the next sampled point 5 m on, so it leads the tangent
    # by half that chord's angle (about 5 degrees).
    tangent = (np.cos(phi), np.sin(phi))
    assert angle_between_deg(heading, tangent) < 6


def test_gate_with_gps_noise_stays_near_the_start():
    found = gate_search(*with_noise(*oval(1.5)))
    assert found is not None
    center, heading, gate = found
    assert np.hypot(*center) < 1.0
    assert angle_between_deg(heading, (1.0, 0.0)) < 10
    assert_gate_across(gate, center, heading)


def test_gate_after_pit_lane_is_where_the_loop_closes():
    found = gate_search(*with_pit_lane(*oval(1.5, start_m=0.0)))
    assert found is not None
    center, heading, gate = found
    # Not where the car started (-110, 0), but on the pit lane within a hitbox
    # of the left turn's exit, where the car first drives back over its path.
    assert center[1] == pytest.approx(0.0)
    assert -50 - TURN_RADIUS_M * np.sin(0.45) < center[0] <= -50
    assert heading == pytest.approx((1.0, 0.0))
    assert_gate_across(gate, center, heading)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (oval(3.5), 3),
        (oval(3.5, start_m=STRAIGHT_M + 20), 3),
        (with_noise(*oval(3.5)), 3),
        # The pit lane's own pass through the gate counts too: the out-lap.
        (with_pit_lane(*oval(3.5, start_m=0.0)), 4),
    ],
    ids=["oval", "mid-turn", "noisy", "pit-lane"],
)
def test_gate_is_crossed_once_per_lap(path, expected):
    x, y = path
    found = gate_search(x, y)
    assert found is not None
    times = pd.Series([at(i / 10) for i in range(len(x))])
    crossings = find_crossings(pd.Series(x), pd.Series(y), times, found[2], None)
    assert len(apply_min_lap_time(crossings, None, MIN_LAP_TIME_S)) == expected
