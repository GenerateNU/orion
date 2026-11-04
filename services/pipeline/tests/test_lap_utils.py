from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.lap_step.lap_constants import EARTH_RADIUS_M
from orion_pipeline.steps.lap_step.lap_utils import (
    Gate,
    apply_min_lap_time,
    build_lap_rows,
    distance_driven,
    find_crossings,
    find_first_revisit,
    find_gate,
    headings,
    to_local_xy,
)

START = datetime(2026, 1, 1, 12, 0, 0)
# Centered on the origin, driven through heading +x, reaching from y = -5 to y = 5.
GATE = Gate(x=0.0, y=0.0, heading_x=1.0, heading_y=0.0, half_width_m=5.0)
# Lap tunables (lap_* fields) at their Settings values.
CTX = RunContext(run_id="run-1")
ONE_DEGREE_M = EARTH_RADIUS_M * np.pi / 180


def at(seconds: float) -> datetime:
    return START + timedelta(seconds=seconds)


def arrays(*values):
    return tuple(np.array(v, dtype=float) for v in values)


def test_to_local_xy_first_point_is_origin():
    x, y = to_local_xy(pd.Series([42.0]), pd.Series([-71.0]))
    assert x.tolist() == pytest.approx([0.0])
    assert y.tolist() == pytest.approx([0.0])


def test_to_local_xy_north_and_east():
    x, y = to_local_xy([0.0, 1.0, 0.0], [0.0, 0.0, 1.0])
    assert x.tolist() == pytest.approx([0.0, 0.0, ONE_DEGREE_M])
    assert y.tolist() == pytest.approx([0.0, ONE_DEGREE_M, 0.0])


def test_to_local_xy_shrinks_east_with_latitude():
    x, _ = to_local_xy([60.0, 60.0], [0.0, 1.0])
    assert x[1] == pytest.approx(ONE_DEGREE_M * 0.5)


def test_to_local_xy_empty():
    x, y = to_local_xy([], [])
    assert x.size == 0 and y.size == 0


def test_headings_use_neighbors():
    hx, hy = headings(*arrays([-1, 0, 1], [0, 0, 0]))
    assert (hx[1], hy[1]) == pytest.approx((1.0, 0.0))


def test_headings_at_ends_use_the_point_itself():
    hx, hy = headings(*arrays([0, 0, 0], [0, 3, 4]))
    assert (hx[0], hy[0]) == pytest.approx((0.0, 1.0))
    assert (hx[2], hy[2]) == pytest.approx((0.0, 1.0))


def test_headings_are_unit_length_even_when_slow():
    hx, hy = headings(*arrays([0, 0.01, 0.02], [0, 0, 0]))
    assert (hx[1], hy[1]) == pytest.approx((1.0, 0.0))


def test_headings_standing_still_are_zero():
    hx, hy = headings(*arrays([0, 0, 0], [0, 0, 0]))
    assert hx.tolist() == [0, 0, 0]
    assert hy.tolist() == [0, 0, 0]


def test_headings_of_one_point_are_zero():
    hx, hy = headings(*arrays([3], [4]))
    assert hx.tolist() == [0] and hy.tolist() == [0]


@pytest.mark.parametrize(
    ("a", "b", "crosses"),
    [
        ((-1, 0), (1, 0), True),  # forward through the middle
        ((-1, 0), (0, 0), True),  # landing exactly on the line counts
        ((0, 0), (1, 0), False),  # starting on the line was already counted
        ((1, 0), (-1, 0), False),  # backwards
        ((-1, 20), (1, 20), False),  # the line's extension, outside the gate
        ((-1, 5), (1, 5), True),  # touching a gate end
        ((-1, -4), (1, -6), True),  # diagonal, through the line inside the gate
        ((-1, 4), (1, 8), False),  # diagonal, through the line outside the gate
        ((-2, -1), (-1, 1), False),  # never reaches the line
    ],
)
def test_find_crossings_single_step(a, b, crosses):
    x, y = arrays([a[0], b[0]], [a[1], b[1]])
    assert find_crossings(x, y, GATE).tolist() == ([1] if crosses else [])


def test_find_crossings_returns_first_point_past():
    x, y = arrays([-2, -1, 1, 2, -1, -2, -1, 1], [0] * 8)
    assert find_crossings(x, y, GATE).tolist() == [2, 7]


def test_find_crossings_empty():
    x, y = arrays([], [])
    assert find_crossings(x, y, GATE).tolist() == []


def test_apply_min_lap_time_drops_jitter():
    crossings = [at(30), at(32), at(40), at(45), at(51)]
    assert apply_min_lap_time(at(0), crossings, 10) == [at(30), at(40), at(51)]


def test_apply_min_lap_time_measures_the_first_crossing_from_the_start():
    # The car starts just behind the line, so its first crossing isn't a lap.
    assert apply_min_lap_time(at(0), [at(3), at(33)], 10) == [at(33)]


def test_apply_min_lap_time_counts_a_crossing_exactly_min_lap_time_later():
    assert apply_min_lap_time(at(0), [at(10), at(20)], 10) == [at(10), at(20)]


def test_apply_min_lap_time_without_crossings():
    assert apply_min_lap_time(at(0), [], 10) == []


def test_build_lap_rows_chains_laps_to_the_end():
    rows = build_lap_rows("run", at(0), at(80), [at(30), at(65)])
    assert rows.to_dict("records") == [
        {"run_id": "run", "lap_id": 1, "start_time": at(0), "end_time": at(30)},
        {"run_id": "run", "lap_id": 2, "start_time": at(30), "end_time": at(65)},
        {"run_id": "run", "lap_id": 3, "start_time": at(65), "end_time": at(80)},
    ]


def test_build_lap_rows_ending_on_a_crossing_adds_no_empty_lap():
    rows = build_lap_rows("run", at(0), at(65), [at(30), at(65)])
    assert rows["end_time"].tolist() == [at(30), at(65)]


def test_build_lap_rows_without_crossings_is_one_lap():
    rows = build_lap_rows("run", at(0), at(30), [])
    assert rows.to_dict("records") == [
        {"run_id": "run", "lap_id": 1, "start_time": at(0), "end_time": at(30)},
    ]


def test_distance_driven_sums_the_steps():
    # Each step is a 3-4-5 triangle.
    assert distance_driven(*arrays([0, 3, 6], [0, 4, 8])).tolist() == [0, 5, 10]


def test_distance_driven_standing_still_stays_zero():
    assert distance_driven(*arrays([2, 2, 2], [1, 1, 1])).tolist() == [0, 0, 0]


def test_distance_driven_empty():
    assert distance_driven(*arrays([], [])).size == 0


def search(xn, yn, tn, radius, min_time, min_distance):
    """find_first_revisit on plain lists, with the thresholds in a readable order."""
    return find_first_revisit(
        *arrays(xn, yn, tn),
        hitbox_radius_m=radius,
        min_revisit_time_s=min_time,
        min_revisit_distance_m=min_distance,
    )


def test_find_first_revisit_finds_return_to_start():
    # A 10 m x 10 m square driven 1 m per second, ending back at the start.
    xn = [*range(10), *[10] * 10, *range(10, 0, -1), *[0] * 11]
    yn = [*[0] * 10, *range(10), *[10] * 10, *range(10, -1, -1)]
    revisit = search(xn, yn, range(len(xn)), 0.5, 5, 30)

    assert revisit == 0


def test_find_first_revisit_needs_enough_distance_driven():
    # Standing still: every point is inside every hitbox, but nothing is driven.
    assert search([0] * 20, [0] * 20, range(20), 3, 5, 50) is None


@pytest.mark.parametrize(("min_time", "revisit"), [(3, 0), (5, None)])
def test_find_first_revisit_needs_enough_time(min_time, revisit):
    # A 40 m loop back to the start, driven in 4 s.
    xn, yn = [0, 20, 20, 0, 0], [0, 0, 20, 20, 0]
    assert search(xn, yn, range(5), 1, min_time, 30) == revisit


def test_find_first_revisit_picks_the_closest_candidate():
    # Two points 2 m apart, then a loop that comes back next to the second one.
    xn = [0, 2, 10, 20, 10, 2.5]
    yn = [0, 0, 0, 10, 20, 0]
    # Both (0, 0) and (2, 0) are inside the hitbox, but (2, 0) is closer.
    assert search(xn, yn, range(6), 3, 1, 20) == 1


def test_find_first_revisit_skips_candidates_without_heading():
    # Parked at the start (points 0-2), then a loop back to (0, 0).
    xn = [0, 0, 0, 10, 20, 10, 0]
    yn = [0, 0, 0, 0, 10, 20, 0.5]
    # Points 0-2 are equally close, but only point 2 has a nonzero heading.
    assert search(xn, yn, range(7), 3, 1, 20) == 2


def test_find_first_revisit_empty_or_single_point_is_none():
    assert search([], [], [], 3, 1, 20) is None
    assert search([0], [0], [0], 3, 1, 20) is None


# The tests below drive realistic tracks through find_gate with the real
# thresholds, the way LapStep does, and check where the gate ends up.

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


def gate_search(x: np.ndarray, y: np.ndarray) -> Gate | None:
    """find_gate on a 10 Hz path, with the lap tunables at their Settings values."""
    return find_gate(
        x,
        y,
        np.arange(len(x)) / 10,
        sample_every=CTX.lap_gate_search_sample_every,
        hitbox_radius_m=CTX.lap_hitbox_radius_m,
        min_revisit_time_s=CTX.lap_min_revisit_time_s,
        min_revisit_distance_m=CTX.lap_min_revisit_distance_m,
        half_width_m=CTX.lap_gate_half_width_m,
    )


def angle_between_deg(a, b) -> float:
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b), -1.0, 1.0))))


def heading_of(gate: Gate) -> tuple[float, float]:
    heading = (gate.heading_x, gate.heading_y)
    assert np.hypot(*heading) == pytest.approx(1.0)
    return heading


def test_oval_gate_is_across_the_start_straight():
    gate = gate_search(*oval(1.5))
    assert gate is not None
    assert (gate.x, gate.y) == pytest.approx((0.0, 0.0))
    assert heading_of(gate) == pytest.approx((1.0, 0.0))
    assert gate.half_width_m == CTX.lap_gate_half_width_m


def test_no_revisit_before_the_loop_is_closed():
    assert gate_search(*oval(0.9)) is None


def test_gate_started_mid_turn_follows_the_turn():
    # 20 m into the first turn, at (50 + 30 sin(phi), 30 (1 - cos(phi))).
    phi = 20 / TURN_RADIUS_M
    start = (50 + TURN_RADIUS_M * np.sin(phi), TURN_RADIUS_M * (1 - np.cos(phi)))
    gate = gate_search(*oval(1.5, start_m=STRAIGHT_M + 20))
    assert gate is not None
    assert (gate.x, gate.y) == pytest.approx(start)
    # Heading comes from the next sampled point 5 m on, so it leads the tangent
    # by half that chord's angle (about 5 degrees).
    tangent = (np.cos(phi), np.sin(phi))
    assert angle_between_deg(heading_of(gate), tangent) < 6


def test_gate_with_gps_noise_stays_near_the_start():
    gate = gate_search(*with_noise(*oval(1.5)))
    assert gate is not None
    assert np.hypot(gate.x, gate.y) < 1.0
    assert angle_between_deg(heading_of(gate), (1.0, 0.0)) < 10


def test_gate_after_pit_lane_is_where_the_loop_closes():
    gate = gate_search(*with_pit_lane(*oval(1.5, start_m=0.0)))
    assert gate is not None
    # Not where the car started (-110, 0), but on the pit lane within a hitbox
    # of the left turn's exit, where the car first drives back over its path.
    assert gate.y == pytest.approx(0.0)
    assert -50 - TURN_RADIUS_M * np.sin(0.45) < gate.x <= -50
    assert heading_of(gate) == pytest.approx((1.0, 0.0))


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (oval(3.5), 3),
        (oval(3.5, start_m=STRAIGHT_M + 20), 3),
        (with_noise(*oval(3.5)), 3),
        # The pit lane passes through the gate 5 s in, under the minimum lap
        # time, so that pass is dropped and the out-lap joins lap 1.
        (with_pit_lane(*oval(3.5, start_m=0.0)), 3),
    ],
    ids=["oval", "mid-turn", "noisy", "pit-lane"],
)
def test_gate_is_crossed_once_per_lap(path, expected):
    x, y = path
    gate = gate_search(x, y)
    assert gate is not None
    crossings = [at(i / 10) for i in find_crossings(x, y, gate)]
    assert len(apply_min_lap_time(at(0), crossings, CTX.lap_min_lap_time_s)) == expected
