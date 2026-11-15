from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.steps.lap_progress_step.ideal_lap import (
    assign_lap_ids,
    build_ideal_lap,
    gate_at,
    lap_stats,
    loops_through_gate,
    pick_median_lap,
)

START = datetime(2026, 1, 1, 12, 0, 0)
RADIUS_M = 50.0
LOOP_M = 2 * np.pi * RADIUS_M
DT_S = 0.1
TUNABLES: dict[str, Any] = {"max_gap_s": 1.0, "max_length_ratio": 1.25}


def drive(laps: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A run around a 50 m circle, one dict per lap.

    Each dict has `secs` (lap time), and optionally `loops` (how many times
    round the circle the lap goes, for merged laps, default 1), `radius` (to
    change the line) and `gap` ((from_s, to_s) within the lap with no points).

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
        r = lap.get("radius", RADIUS_M)
        keep = np.ones(n, dtype=bool)
        if "gap" in lap:
            lo, hi = lap["gap"]
            keep = (frac * lap["secs"] < lo) | (frac * lap["secs"] >= hi)
        times.extend(t0 + frac[keep] * lap["secs"])
        xs.extend(r * np.sin(theta[keep]))
        ys.extend(r * (1 - np.cos(theta[keep])))
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


def ideal_lap_id(laps) -> int | None:
    positions, lap_rows = drive(laps)
    ideal = build_ideal_lap(positions, lap_rows, **TUNABLES, spacing_m=1.0)
    return None if ideal is None else ideal.lap_id


def test_picks_the_median_lap_time():
    laps = [{"secs": 20}, {"secs": 30}, {"secs": 34}, {"secs": 31}, {"secs": 50}]
    # Inner laps 2-4 take 30, 34, 31 s: the median is lap 4 (31 s).
    assert ideal_lap_id(laps) == 4


def test_even_count_takes_the_faster_middle_lap():
    laps = [
        {"secs": 20},
        {"secs": 30},
        {"secs": 36},
        {"secs": 33},
        {"secs": 40},
        {"secs": 9},
    ]
    # Inner laps 2-5 take 30, 36, 33, 40 s: the middle two are 33 and 36.
    assert ideal_lap_id(laps) == 4


def test_first_and_last_laps_never_count():
    # The first and last laps are the median times, but they're excluded.
    laps = [{"secs": 31}, {"secs": 25}, {"secs": 40}, {"secs": 31}]
    assert ideal_lap_id(laps) == 2


def test_merged_laps_are_skipped():
    # Lap 3 is three loops merged into one (a missed gate crossing). Its 95 s
    # would otherwise be the median of 30, 95, 95, 32.
    laps = [
        {"secs": 20},
        {"secs": 30},
        {"secs": 95, "loops": 3},
        {"secs": 95, "loops": 3},
        {"secs": 32},
        {"secs": 20},
    ]
    assert ideal_lap_id(laps) == 2


def test_laps_with_holes_in_the_data_are_skipped():
    laps = [
        {"secs": 20},
        {"secs": 31, "gap": (10, 15)},
        {"secs": 31, "gap": (10, 15)},
        {"secs": 30},
        {"secs": 35},
        {"secs": 20},
    ]
    assert ideal_lap_id(laps) == 4


def test_missing_data_at_a_lap_edge_counts_as_a_hole():
    positions, lap_rows = drive(
        [{"secs": 20}, {"secs": 30, "gap": (0, 3)}, {"secs": 20}]
    )
    stats = lap_stats(positions, lap_rows)
    assert stats["max_gap_s"].iloc[1] == pytest.approx(3.0, abs=0.01)


def test_no_qualifying_lap_gives_none():
    assert ideal_lap_id([{"secs": 30}, {"secs": 30}]) is None
    assert (
        ideal_lap_id([{"secs": 20}, {"secs": 30, "gap": (5, 20)}, {"secs": 20}]) is None
    )
    empty = pd.DataFrame(columns=["time", "x", "y"])
    assert (
        build_ideal_lap(empty, drive([{"secs": 30}])[1], **TUNABLES, spacing_m=1.0)
        is None
    )


def test_ideal_lap_is_evenly_spaced_from_the_gate():
    positions, lap_rows = drive([{"secs": 20}, {"secs": 30}, {"secs": 30}])
    ideal = build_ideal_lap(positions, lap_rows, **TUNABLES, spacing_m=2.0)

    assert ideal is not None
    assert ideal.length_m == pytest.approx(LOOP_M, rel=0.01)
    steps = np.hypot(np.diff(ideal.x), np.diff(ideal.y))
    assert steps == pytest.approx(np.full(len(steps), 2.0), rel=0.01)
    # Starts at the gate, the lap's first point, and percent rises from 0.
    assert (ideal.x[0], ideal.y[0]) == pytest.approx((0.0, 0.0), abs=1e-9)
    assert ideal.percent[0] == 0.0
    assert ideal.percent[-1] < 100.0
    assert np.all(np.diff(ideal.percent) > 0)


def test_lap_stats_measures_each_lap():
    positions, lap_rows = drive([{"secs": 20}, {"secs": 30, "loops": 2}, {"secs": 25}])
    stats = lap_stats(positions, lap_rows)

    assert stats["duration_s"].tolist() == pytest.approx([20, 30, 25])
    assert stats["length_m"].tolist() == pytest.approx(
        [LOOP_M, 2 * LOOP_M, LOOP_M], rel=0.01
    )
    assert stats["max_gap_s"].tolist() == pytest.approx([DT_S] * 3, abs=1e-6)


def test_pick_median_lap_respects_its_tunables():
    stats = pd.DataFrame(
        {
            "lap_id": [1, 2, 3, 4, 5],
            "duration_s": [10.0, 30.0, 60.0, 61.0, 10.0],
            "length_m": [300.0, 300.0, 600.0, 600.0, 300.0],
            "max_gap_s": [0.0, 0.0, 2.0, 0.0, 0.0],
        }
    )
    assert pick_median_lap(stats, **TUNABLES) == 2
    assert pick_median_lap(stats, max_gap_s=1.0, max_length_ratio=2.0) == 2
    assert pick_median_lap(stats, max_length_ratio=2.0, max_gap_s=5.0) == 3


def test_assign_lap_ids_uses_half_open_laps():
    _, lap_rows = drive([{"secs": 10}, {"secs": 10}])
    times = pd.Series(
        pd.to_datetime([START + timedelta(seconds=s) for s in (0, 9.9, 10, 20)])
    )
    assert assign_lap_ids(times, lap_rows).tolist() == [1, 1, 2, 2]


# ---- Fallback: loops cut from the positions --------------------------------


def test_gate_at_faces_the_direction_of_travel():
    positions, _ = drive([{"secs": 30}])
    gate = gate_at(positions, 0, half_width_m=15.0)
    # The circle starts at (0, 0) heading +x.
    assert gate is not None
    assert (gate.heading_x, gate.heading_y) == pytest.approx((1.0, 0.0), abs=0.02)
    stopped = pd.DataFrame({"time": positions["time"][:3], "x": 0.0, "y": 0.0})
    assert gate_at(stopped, 1, half_width_m=15.0) is None


def test_loops_through_gate_cuts_one_loop_per_pass():
    # One lap of three loops, gate 1 s in: passes at 1 s, ~33 s and ~64 s.
    positions, _ = drive([{"secs": 95, "loops": 3}])
    gate = gate_at(positions, 10, half_width_m=15.0)
    assert gate is not None
    loops = loops_through_gate(positions, gate, min_loop_time_s=10.0)

    durations = (loops["end_time"] - loops["start_time"]).dt.total_seconds()
    assert loops["lap_id"].tolist() == [1, 2]
    assert durations.tolist() == pytest.approx([95 / 3, 95 / 3], abs=0.2)


def test_loops_through_gate_ignores_quick_repasses():
    # Passes at 1 s, ~33 s and ~64 s. With a 70 s minimum only the first counts,
    # so there's no full loop.
    positions, _ = drive([{"secs": 95, "loops": 3}])
    gate = gate_at(positions, 10, half_width_m=15.0)
    assert gate is not None
    assert loops_through_gate(positions, gate, min_loop_time_s=70.0).empty


def test_fallback_is_used_only_when_no_lap_qualifies():
    calls = []

    def fallback():
        calls.append(1)
        return None

    positions, lap_rows = drive([{"secs": 20}, {"secs": 30}, {"secs": 30}])
    build_ideal_lap(
        positions, lap_rows, **TUNABLES, spacing_m=1.0, fallback_gate=fallback
    )
    assert calls == []

    positions, lap_rows = drive([{"secs": 30}, {"secs": 30}])
    assert (
        build_ideal_lap(
            positions, lap_rows, **TUNABLES, spacing_m=1.0, fallback_gate=fallback
        )
        is None
    )
    assert calls == [1]


def test_fallback_cuts_the_median_loop():
    # Five loops, each at its own speed and on its own line (radius). Every
    # circle passes through (0, 0) heading +x, so the loops join up there.
    loops = [
        {"secs": 25, "radius": 50.0},  # before the first pass: not a full trip
        {"secs": 36, "radius": 50.0},  # trip 1
        {"secs": 30, "radius": 46.0},  # trip 2
        {"secs": 40, "radius": 54.0},  # trip 3
        {"secs": 25, "radius": 50.0},  # after the last pass: not a full trip
    ]
    positions, loop_rows = drive(loops)
    # Lap detection missed every crossing: the whole run is one lap.
    one_lap = pd.DataFrame(
        {
            "lap_id": [1],
            "start_time": [loop_rows["start_time"].iloc[0]],
            "end_time": [loop_rows["end_time"].iloc[-1]],
        }
    )
    ideal = build_ideal_lap(
        positions,
        one_lap,
        **TUNABLES,
        spacing_m=1.0,
        fallback_gate=lambda: gate_at(positions, 0, half_width_m=15.0),
        min_loop_time_s=10.0,
    )

    # Trips take 36, 30 and 40 s: the median is trip 1 (36 s), on the 50 m line.
    # Its length tells it apart from trip 2 (46 m line) and trip 3 (54 m line).
    assert ideal is not None
    assert ideal.lap_id == 1
    assert ideal.length_m == pytest.approx(2 * np.pi * 50.0, rel=0.01)
    assert ideal.length_m != pytest.approx(2 * np.pi * 46.0, rel=0.01)
    assert ideal.length_m != pytest.approx(2 * np.pi * 54.0, rel=0.01)
