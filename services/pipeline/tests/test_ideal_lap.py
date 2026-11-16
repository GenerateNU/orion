from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.steps.lap_progress_step.ideal_lap import (
    assign_lap_ids,
    choose_laps,
    find_medoid,
    lap_stats,
    laps_from_ids,
)
from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    IdealLap,
    mean_distance,
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
    round the circle the lap goes, for merged laps, default 1) and `gap`
    ((from_s, to_s) within the lap with no points).

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
        keep = np.ones(n, dtype=bool)
        if "gap" in lap:
            lo, hi = lap["gap"]
            keep = (frac * lap["secs"] < lo) | (frac * lap["secs"] >= hi)
        times.extend(t0 + frac[keep] * lap["secs"])
        xs.extend(RADIUS_M * np.sin(theta[keep]))
        ys.extend(RADIUS_M * (1 - np.cos(theta[keep])))
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


def chosen(laps: list[dict[str, Any]], **tunables: float) -> list[int]:
    positions, lap_rows = drive(laps)
    return choose_laps(
        lap_stats(positions["time"], lap_rows),
        **{"max_gap_s": 1.0, "max_lap_time_ratio": 1.5, **tunables},
    )


def circle_lap(
    radius_m: float = RADIUS_M, wobble_m: float = 0.0, phase: float = 0.0
) -> IdealLap:
    """A circle through the gate at (0, 0), heading +x, resampled 1 m apart.

    With `wobble_m`, the line weaves that far either side, five times a lap,
    starting at `phase`. The weave fades to nothing at the gate.
    """
    theta = np.linspace(0, 2 * np.pi, 2000, endpoint=False)
    r = radius_m + wobble_m * np.sin(5 * theta + phase) * np.sin(theta / 2)
    return resample(r * np.sin(theta), radius_m - r * np.cos(theta), 1.0)


# ---- Which laps the ideal lap is picked from -----------------------------------------


def test_choose_laps_skips_the_first_and_last_laps():
    assert chosen([{"secs": 50}] * 5) == [2, 3, 4]


def test_choose_laps_skips_a_lap_with_a_long_stop():
    laps = [{"secs": 50}, {"secs": 50}, {"secs": 900}, {"secs": 52}, {"secs": 49}]
    assert chosen([*laps, {"secs": 50}]) == [2, 4, 5]


def test_choose_laps_skips_merged_laps():
    # Lap 3 is two loops merged into one by a missed gate crossing.
    laps = [{"secs": 50}, {"secs": 50}, {"secs": 100, "loops": 2}, {"secs": 51}]
    assert chosen([*laps, {"secs": 49}, {"secs": 50}]) == [2, 4, 5]


def test_choose_laps_skips_laps_with_holes_in_the_data():
    laps: list[dict[str, Any]] = [
        {"secs": 50},
        {"secs": 50, "gap": (10, 15)},
        {"secs": 50},
        {"secs": 50},
    ]
    assert chosen(laps) == [3]


def test_choose_laps_respects_its_tunables():
    laps = [{"secs": 50}, {"secs": 50}, {"secs": 70}, {"secs": 50}, {"secs": 50}]
    assert chosen(laps) == [2, 3, 4]
    assert chosen(laps, max_lap_time_ratio=1.2) == [2, 4]


def test_too_few_laps_choose_nothing():
    assert chosen([{"secs": 50}, {"secs": 50}]) == []
    assert chosen([{"secs": 50}, {"secs": 50, "gap": (5, 20)}, {"secs": 50}]) == []


def test_lap_stats_counts_missing_data_at_a_lap_edge_as_a_hole():
    positions, lap_rows = drive(
        [{"secs": 20}, {"secs": 30, "gap": (0, 3)}, {"secs": 20}]
    )
    stats = lap_stats(positions["time"], lap_rows)
    assert stats["max_gap_s"].iloc[1] == pytest.approx(3.0, abs=0.01)
    assert stats["duration_s"].tolist() == pytest.approx([20, 30, 20])


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
    smooth = smooth_loop(jittery, spacing_m=1.0, smoothing_m=0.25)

    # Closer to the true line than the jittery points were, and evenly spaced
    # from the gate around one loop. The jitter is a little more than the
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


# ---- Lap ids --------------------------------------------------------------------


def test_assign_lap_ids_uses_half_open_laps():
    _, lap_rows = drive([{"secs": 10}, {"secs": 10}])
    times = pd.Series(
        pd.to_datetime([START + timedelta(seconds=s) for s in (0, 9.9, 10, 20)])
    )
    assert assign_lap_ids(times, lap_rows).tolist() == [1, 1, 2, 2]


def test_laps_from_ids_rebuilds_lap_windows():
    positions, lap_rows = drive([{"secs": 20}, {"secs": 30}, {"secs": 25}])
    lap_ids = assign_lap_ids(positions["time"], lap_rows)
    laps = laps_from_ids(positions["time"], lap_ids)

    assert laps["lap_id"].tolist() == [1, 2, 3]
    # Each lap starts at its first point and ends where the next one starts.
    assert laps["start_time"].tolist() == lap_rows["start_time"].tolist()
    assert laps["end_time"].tolist()[:2] == lap_rows["start_time"].tolist()[1:]
    # The last lap ends at the run's last point.
    assert laps["end_time"].iloc[-1] == positions["time"].iloc[-1]
