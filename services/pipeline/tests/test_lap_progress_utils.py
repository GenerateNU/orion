from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    IdealLap,
    assign_lap_ids,
    distance_along,
    find_medoid,
    lap_percents,
    mean_distance,
    middle_laps,
    resample,
    smooth_loop,
)

START = datetime(2026, 1, 1, 12, 0, 0)
RADIUS_M = 50.0
LOOP_M = 2 * np.pi * RADIUS_M
DT_S = 0.1


def drive(laps: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A run around a 50 m circle, one dict per lap.

    Each dict has `secs` (lap time), and optionally `loops` (how many times
    round the circle the lap goes, for merged laps, default 1).

    Args:
        laps: One dict per lap, as above.

    Returns:
        (positions with time/x/y, laps rows).
    """
    times, xs, ys, starts, ends = [], [], [], [], []
    t0 = 0.0
    for lap in laps:
        n = round(lap["secs"] / DT_S)
        frac = np.arange(n) / n
        theta = 2 * np.pi * lap.get("loops", 1) * frac
        times.extend(t0 + frac * lap["secs"])
        xs.extend(RADIUS_M * np.sin(theta))
        ys.extend(RADIUS_M * (1 - np.cos(theta)))
        starts.append(t0)
        t0 += lap["secs"]
        ends.append(t0)
    at = [START + timedelta(seconds=float(s)) for s in times]
    positions = pd.DataFrame({"time": pd.to_datetime(at), "x": xs, "y": ys})
    lap_rows = pd.DataFrame(
        {
            "lap_id": range(1, len(laps) + 1),
            "start_time": pd.to_datetime(
                [START + timedelta(seconds=s) for s in starts]
            ),
            "end_time": pd.to_datetime([START + timedelta(seconds=s) for s in ends]),
        }
    )
    return positions, lap_rows


def middle_lap_lengths(laps: list[dict[str, Any]]) -> list[float]:
    """The lengths of the laps `middle_laps` keeps, in meters."""
    positions, lap_rows = drive(laps)
    lap_ids = assign_lap_ids(positions["time"], lap_rows)
    kept = middle_laps(positions["x"].to_numpy(), positions["y"].to_numpy(), lap_ids)
    return [lap.length_m for lap in kept]


def circle_lap(
    radius_m: float = RADIUS_M, wobble_m: float = 0.0, phase: float = 0.0
) -> IdealLap:
    """A circle through the line at (0, 0), heading +x, resampled 1 m apart.

    With `wobble_m`, the line weaves that far either side, five times a lap,
    starting at `phase`. The weave fades to nothing at the line.
    """
    theta = np.linspace(0, 2 * np.pi, 2000, endpoint=False)
    r = radius_m + wobble_m * np.sin(5 * theta + phase) * np.sin(theta / 2)
    return resample(r * np.sin(theta), radius_m - r * np.cos(theta), 1.0)


# ---- Which laps the ideal lap is picked from -----------------------------------------


def test_middle_laps_skips_the_first_and_last_laps():
    assert middle_lap_lengths([{"secs": 50}] * 5) == pytest.approx(
        [LOOP_M] * 3, rel=0.01
    )


def test_middle_laps_skips_merged_laps():
    # Lap 3 is two loops merged into one by a missed crossing.
    laps = [{"secs": 50}, {"secs": 50}, {"secs": 100, "loops": 2}, {"secs": 51}]
    lengths = middle_lap_lengths([*laps, {"secs": 49}, {"secs": 50}])
    assert lengths == pytest.approx([LOOP_M] * 3, rel=0.01)


def test_middle_laps_keeps_slow_laps():
    # A long stop doesn't make a lap longer, so it can still be the ideal lap.
    laps = [{"secs": 50}, {"secs": 50}, {"secs": 900}, {"secs": 50}, {"secs": 50}]
    assert len(middle_lap_lengths(laps)) == 3


def test_too_few_laps_have_no_middle_laps():
    assert middle_lap_lengths([{"secs": 50}, {"secs": 50}]) == []


# ---- Picking the ideal lap ---------------------------------------------------


def test_resample_is_evenly_spaced_from_the_first_point():
    positions, _ = drive([{"secs": 30}])
    path = resample(positions["x"].to_numpy(), positions["y"].to_numpy(), 2.0)

    assert path.length_m == pytest.approx(LOOP_M, rel=0.01)
    steps = np.hypot(np.diff(path.x), np.diff(path.y))
    assert steps == pytest.approx(np.full(len(steps), 2.0), rel=0.01)
    assert (path.x[0], path.y[0]) == pytest.approx((0.0, 0.0), abs=1e-9)
    assert path.s[0] == 0.0
    assert np.diff(path.s) == pytest.approx(np.full(len(steps), 2.0))


def test_smooth_loop_irons_out_jitter_without_moving_the_line():
    circle = circle_lap()
    rng = np.random.default_rng(0)
    jittery = IdealLap(
        circle.x + rng.normal(0, 0.3, len(circle.x)),
        circle.y + rng.normal(0, 0.3, len(circle.y)),
        circle.s,
        circle.length_m,
    )
    smooth = smooth_loop(jittery)

    # Closer to the true line than the jittery points were, and evenly spaced
    # from the line around one loop. The jitter is a little more than the
    # smoothing allows for, so a trace of it (about 1% length) is left.
    assert mean_distance(circle, smooth.x, smooth.y) < mean_distance(
        circle, jittery.x, jittery.y
    )
    jittery_length = resample(jittery.x, jittery.y, 1.0).length_m
    assert smooth.length_m < jittery_length
    assert smooth.length_m == pytest.approx(LOOP_M, rel=0.02)
    assert (smooth.x[0], smooth.y[0]) == pytest.approx((0.0, 0.0), abs=1.0)
    assert smooth.s[0] == 0.0
    assert np.diff(smooth.s) == pytest.approx(np.ones(len(smooth.s) - 1))


def test_medoid_is_a_typical_lap_not_the_odd_one():
    typical = [circle_lap(wobble_m=w) for w in (0.0, 0.5, 1.0)]
    odd = circle_lap(radius_m=RADIUS_M + 8.0)
    assert find_medoid([odd, *typical]) != 0
    assert find_medoid([*typical, odd]) != len(typical)


def test_medoid_is_the_middle_line():
    # Lines 2 m apart: the one in the middle is closest to the rest.
    laps = [circle_lap(radius_m=RADIUS_M + d) for d in (-4.0, 2.0, 0.0, -2.0, 4.0)]
    assert find_medoid(laps) == 2
    assert find_medoid(laps[:1]) == 0


def test_mean_distance_measures_to_the_nearest_point():
    lap = circle_lap()
    assert mean_distance(lap, lap.x, lap.y) == pytest.approx(0.0, abs=1e-9)
    # Points 3 m outside the circle.
    theta = np.linspace(0, 2 * np.pi, 50, endpoint=False)
    r = RADIUS_M + 3.0
    x, y = r * np.sin(theta), RADIUS_M - r * np.cos(theta)
    assert mean_distance(lap, x, y) == pytest.approx(3.0, abs=0.05)


# ---- Lap ids and matching -----------------------------------------------------------


def test_assign_lap_ids_uses_half_open_laps():
    _, lap_rows = drive([{"secs": 10}, {"secs": 10}])
    times = pd.Series(
        pd.to_datetime([START + timedelta(seconds=s) for s in (0, 9.9, 10, 20)])
    )
    assert assign_lap_ids(times, lap_rows).tolist() == [1, 1, 2, 2]


def test_distance_along_follows_the_car_between_ideal_lap_points():
    # Ideal lap points 1 m apart; the car every 1 cm, half a meter outside it.
    theta = np.linspace(0.5, 0.6, 500)
    r = RADIUS_M + 0.5
    x, y = r * np.sin(theta), RADIUS_M - r * np.cos(theta)

    s = distance_along(circle_lap(), x, y)

    assert s == pytest.approx(RADIUS_M * theta, abs=0.05)


# ---- Percentages -------------------------------------------------------------------


def percents(s, time_s=None, lap_ids=None, length_m=100.0):
    """`lap_percents` for one lap of a 100 m ideal lap (so meters = percent), with
    points 100 s apart (so no match is too far ahead) unless `time_s` is given."""
    s = np.array(s, dtype=float)
    time_s = 100.0 * np.arange(len(s)) if time_s is None else time_s
    times = pd.Series(START + pd.to_timedelta(time_s, unit="s"))
    lap_ids = np.ones(len(s), dtype=np.int64) if lap_ids is None else lap_ids
    return lap_percents(s, times, np.array(lap_ids, dtype=np.int64), length_m)


@pytest.mark.parametrize(
    ("s", "expected"),
    [
        # Starts just before the line: reads 0, not 99.5.
        ([99.5, 0.5, 50.0, 99.0], [0.0, 0.5, 50.0, 99.0]),
        # Never goes backwards.
        ([30.0, 20.0], [30.0, 30.0]),
        # Ends just past the line: reads 100, not 0.5.
        ([2.0, 50.0, 97.0, 0.5, 1.5], [2.0, 50.0, 97.0, 100.0, 100.0]),
        # Two loops merged into one lap: stays at 100 for the second loop.
        ([10.0, 40.0, 70.0, 95.0, 5.0, 40.0], [10.0, 40.0, 70.0, 95.0, 100.0, 100.0]),
    ],
)
def test_lap_percents(s, expected):
    assert percents(s).tolist() == pytest.approx(expected)


def test_each_lap_starts_again():
    percent = percents([10.0, 50.0, 99.0, 1.0, 5.0], lap_ids=[1, 1, 1, 2, 2])
    assert percent.tolist() == pytest.approx([10.0, 50.0, 99.0, 1.0, 5.0])


def test_a_point_too_far_ahead_keeps_the_previous_percentage():
    # 0.1 s apart: the 60 m point is far beyond 40 m/s * 0.1 s + 10 m.
    percent = percents([10, 11, 60, 13, 14], time_s=[0, 0.1, 0.2, 0.3, 0.4])
    assert percent.tolist() == pytest.approx([10, 11, 11, 13, 14])


def test_a_bad_backward_point_keeps_the_previous_percentage():
    # And the points after it aren't treated as jumps from it.
    percent = percents([10, 11, 2, 13, 14], time_s=[0, 0.1, 0.2, 0.3, 0.4])
    assert percent.tolist() == pytest.approx([10, 11, 11, 13, 14])


def test_the_jump_check_allows_more_after_a_gap():
    # On a 1 km lap: 30 m ahead after 0.1 s is too far (40 m/s * 0.1 s + 10 m),
    # but 200 m ahead after 5 s isn't (40 m/s * 5 s + 10 m).
    percent = percents([100, 130, 300], time_s=[0, 0.1, 5], length_m=1000.0)
    assert percent.tolist() == pytest.approx([10, 10, 30])


def test_a_bad_match_just_over_half_a_lap_ahead_doesnt_freeze_the_lap():
    s = np.arange(0.0, 50.0, 2.5)
    s[4] += 51.0
    percent = percents(s, time_s=0.1 * np.arange(len(s)))

    expected = np.arange(0.0, 50.0, 2.5)
    expected[4] = expected[3]  # The bad point keeps the percentage before it.
    assert percent.tolist() == pytest.approx(expected.tolist())
