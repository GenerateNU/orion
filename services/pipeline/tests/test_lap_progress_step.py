from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.lap_progress_step import lap_progress_constants
from orion_pipeline.steps.lap_progress_step.ideal_lap import assign_lap_ids
from orion_pipeline.steps.lap_progress_step.lap_progress_step import (
    IDEAL_LAP_TABLE,
    LapProgressStep,
)
from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    lap_percentages,
    to_lat_lon,
)
from orion_pipeline.steps.lap_step.lap_utils import to_local_xy

ORIGIN_LAT, ORIGIN_LON = 42.34, -71.09
START = datetime(2026, 1, 1, 12, 0, 0)
DT_S = 0.1

# A stadium: two 200 m straights joined by 50 m-radius half circles.
STRAIGHT_M, RADIUS_M = 200.0, 50.0
PERIMETER_M = 2 * STRAIGHT_M + 2 * np.pi * RADIUS_M


def stadium(u: np.ndarray, offset_m: np.ndarray | float = 0.0):
    """Point at fraction `u` of the centerline, shifted `offset_m` to the left.

    Starts at the middle of the bottom straight, driving +x (counterclockwise).
    """
    d = (np.asarray(u) % 1.0) * PERIMETER_M
    half = STRAIGHT_M / 2
    arc = np.pi * RADIUS_M
    x, y, nx, ny = (np.zeros_like(d) for _ in range(4))
    legs = [
        d < half,
        (d >= half) & (d < half + arc),
        (d >= half + arc) & (d < half + arc + STRAIGHT_M),
        (d >= half + arc + STRAIGHT_M) & (d < half + 2 * arc + STRAIGHT_M),
        d >= half + 2 * arc + STRAIGHT_M,
    ]
    # Bottom straight, heading +x. Left is +y.
    m = legs[0] | legs[4]
    along = np.where(legs[0], d, d - PERIMETER_M)
    x[m], y[m], nx[m], ny[m] = along[m], 0.0, 0.0, 1.0
    # Right half circle, centered (half, R).
    m = legs[1]
    a = (d[m] - half) / RADIUS_M - np.pi / 2
    x[m], y[m] = half + RADIUS_M * np.cos(a), RADIUS_M + RADIUS_M * np.sin(a)
    nx[m], ny[m] = -np.cos(a), -np.sin(a)
    # Top straight, heading -x.
    m = legs[2]
    x[m], y[m], nx[m], ny[m] = half - (d[m] - half - arc), 2 * RADIUS_M, 0.0, -1.0
    # Left half circle, centered (-half, R).
    m = legs[3]
    a = (d[m] - half - arc - STRAIGHT_M) / RADIUS_M + np.pi / 2
    x[m], y[m] = -half + RADIUS_M * np.cos(a), RADIUS_M + RADIUS_M * np.sin(a)
    nx[m], ny[m] = -np.cos(a), -np.sin(a)
    return x + offset_m * nx, y + offset_m * ny


def drive(laps: list[dict[str, Any]], start_u: float = 0.0, end_u: float = 1.0):
    """Sample a run that drives the given laps around the stadium.

    Each lap dict has `speed` (m/s, base), `line` (meters left of the
    centerline, as an amplitude that varies around the lap), and optionally
    `wiggle` (a second, shorter-period line change) and `loops` (how many times
    round the lap goes, for merged laps, default 1).

    Args:
        laps: One dict per lap, as above.
        start_u: Where on the track the first lap starts.
        end_u: Where on the track the last lap ends.

    Returns:
        (positions frame, laps frame, track fraction of each point).
    """
    us, offsets, lap_ids = [], [], []
    for i, lap in enumerate(laps):
        at = start_u if i == 0 else 0.0
        stop = end_u if i == len(laps) - 1 else float(lap.get("loops", 1))
        while at < stop:
            # Slower in the corners, so speed varies within the lap too.
            v = lap["speed"] * (1 - 0.3 * np.cos(4 * np.pi * at) ** 2)
            us.append(at % 1.0)
            # Zero at the gate, so the line is continuous from lap to lap.
            offsets.append(
                lap["line"] * np.sin(4 * np.pi * at)
                + lap.get("wiggle", 0.0) * np.sin(6 * np.pi * at)
            )
            lap_ids.append(i + 1)
            at += v * DT_S / PERIMETER_M
    u = np.array(us)
    x, y = stadium(u, np.array(offsets))
    positions = track_frame(x, y)
    positions["lap_id"] = lap_ids
    lap_rows = (
        positions.groupby("lap_id")["time"]
        .agg(start_time="min", end_time="max")
        .reset_index()
    )
    # Laps meet: each ends where the next starts, like the lap step writes them.
    lap_rows["end_time"] = [
        *lap_rows["start_time"].iloc[1:],
        lap_rows["end_time"].iloc[-1],
    ]
    return positions.drop(columns="lap_id"), lap_rows, u


def track_frame(x: np.ndarray, y: np.ndarray) -> pd.DataFrame:
    lat, lon = to_lat_lon(x, y, ORIGIN_LAT, ORIGIN_LON)
    time = START + pd.to_timedelta(np.arange(len(x)) * DT_S, unit="s")
    return pd.DataFrame({"time": time, "lattitude": lat, "longitude": lon})


def run_step(positions: pd.DataFrame, laps: pd.DataFrame):
    """Run the step without a database. Returns (progress, ideal lap, writer)."""
    reader = MagicMock()
    reader.read_frame.side_effect = [positions, laps]
    writer = MagicMock()
    LapProgressStep(reader=reader, writer=writer).run(RunContext(run_id="run-1"))
    written = {call.args[0]: call.args[1] for call in writer.append.call_args_list}
    return written.get("lap_progress"), written.get(IDEAL_LAP_TABLE), writer


VARIED_LAPS = [
    {"speed": 20.0, "line": 0.0},
    {"speed": 22.0, "line": 0.5},
    {"speed": 30.0, "line": 3.0},
    {"speed": 25.0, "line": -2.5, "wiggle": 1.5},
    {"speed": 18.0, "line": 2.0, "wiggle": -2.0},
    {"speed": 27.0, "line": -1.0},
    {"speed": 21.0, "line": 1.5},
]


def percent_at(progress: pd.DataFrame, u: np.ndarray, lap_id: int, grid: np.ndarray):
    """One lap's percentage at track fractions `grid`, interpolated."""
    mask = (progress["lap_id"] == lap_id).to_numpy()
    lap_percent = progress.loc[mask, "lap_percent"].astype(float).to_numpy()
    return np.interp(grid, u[mask], lap_percent)


def test_same_place_gets_same_percentage_across_speeds_and_lines():
    positions, laps, u = drive(VARIED_LAPS)
    progress, ideal, _ = run_step(positions, laps)

    assert progress["lap_percent"].notna().all()
    grid = np.linspace(0.02, 0.98, 49)
    per_lap = np.array([percent_at(progress, u, lap, grid) for lap in laps["lap_id"]])
    spread = per_lap.max(axis=0) - per_lap.min(axis=0)
    assert spread.max() < 1.0
    # And it tracks distance around the track, not time.
    assert per_lap.mean(axis=0) == pytest.approx(100 * grid, abs=1.5)
    assert ideal["lap_percent"].iloc[0] == 0.0


def test_percentages_rise_through_each_lap_without_jumps():
    positions, laps, _ = drive(VARIED_LAPS, start_u=0.4, end_u=0.7)
    progress, _, _ = run_step(positions, laps)

    for _, lap in progress.groupby("lap_id"):
        steps = np.diff(lap["lap_percent"].astype(float).to_numpy())
        assert (steps >= 0).all()
        # At most 30 m/s * 0.1 s = 3 m per point, under 0.5% of the lap.
        assert steps.max() < 0.6


def test_hairpin_parallel_sections_never_swap():
    # Out and back along two straights 8 m apart, joined by tight turns, at
    # 25 m/s (2.5 m per point), five times.
    step_m, straight, r = 2.5, 300.0, 4.0
    out = np.arange(0, straight, step_m)
    turn = np.arange(0, np.pi, step_m / r)
    x = np.concatenate(
        [out, straight + r * np.sin(turn), straight - out, -r * np.sin(turn)]
    )
    y = np.concatenate(
        [0 * out, r - r * np.cos(turn), 0 * out + 2 * r, r + r * np.cos(turn)]
    )
    n = len(x)
    positions = track_frame(np.tile(x, 5), np.tile(y, 5))
    starts = positions["time"].iloc[::n].tolist()
    laps = pd.DataFrame(
        {
            "lap_id": range(1, 6),
            "start_time": starts,
            "end_time": [*starts[1:], positions["time"].iloc[-1]],
        }
    )
    progress, _, _ = run_step(positions, laps)

    percent = progress["lap_percent"].astype(float).to_numpy()
    for k in range(5):
        lap = percent[k * n : (k + 1) * n]
        assert not np.isnan(lap).any()
        assert np.abs(np.diff(lap)).max() < 1.0
    # 50 m down the return straight is well past halfway, not mirrored onto the
    # outbound straight 8 m away.
    back = 2 * n + len(out) + len(turn) + np.arange(20, 24)
    assert percent[back].min() > 50


def test_off_track_points_get_no_percentage():
    positions, laps, u = drive(VARIED_LAPS)
    x, y = to_local_xy(positions["lattitude"], positions["longitude"])
    # In lap 3, ease 30 m off the track into a "pit lane" and back.
    lap3 = assign_lap_ids(positions["time"], laps) == 3
    detour = lap3 & (u > 0.02) & (u < 0.2)
    bump = np.sin(np.pi * (u - 0.02) / 0.18) ** 2
    y = np.where(detour, y - 30 * bump, y)
    positions[["lattitude", "longitude"]] = np.column_stack(
        to_lat_lon(x, y, ORIGIN_LAT, ORIGIN_LON)
    )
    progress, _, _ = run_step(positions, laps)

    percent = progress["lap_percent"]
    far = detour & (30 * bump > 20)
    assert far.any()
    # Really None (written as NULL), not NaN, even mixed in with numbers.
    assert percent[far].map(lambda v: v is None).all()
    # Back on track afterwards, and everywhere off the detour.
    assert percent[~detour].notna().all()


def test_off_track_percent_is_written_as_none_not_nan(monkeypatch):
    # Every point is "too slow", so none gets a percentage. A NaN would be
    # written to the database as a number; None is written as NULL.
    monkeypatch.setattr(lap_progress_constants, "MIN_SPEED_MPS", 1000.0)
    positions, laps, _ = drive(VARIED_LAPS[:4])
    progress, _, _ = run_step(positions, laps)

    assert progress["lap_percent"].map(lambda v: v is None).all()


def test_rerun_clears_both_tables_before_writing():
    positions, laps, _ = drive(VARIED_LAPS[:4])
    _, _, writer = run_step(positions, laps)

    deletes = [c.args for c in writer.delete_for_run.call_args_list]
    assert deletes == [("lap_progress", "run-1"), (IDEAL_LAP_TABLE, "run-1")]
    names = [c[0] for c in writer.method_calls]
    assert names.index("append") > max(
        i for i, n in enumerate(names) if n == "delete_for_run"
    )


def test_one_lap_run_still_gets_percentages():
    # Lap detection found no crossing: the whole run, three loops, is lap 1.
    positions, laps, u = drive([{**VARIED_LAPS[1], "loops": 3}], end_u=3.0)
    progress, ideal, _ = run_step(positions, laps)

    assert len(ideal) == pytest.approx(PERIMETER_M, rel=0.05)
    percent = progress["lap_percent"].astype(float).to_numpy()
    assert np.isnan(percent).mean() < 0.01
    # The same spot reads the same on every loop.
    loop = np.cumsum(np.r_[0, np.diff(u) < -0.5])
    at_quarter = [np.interp(0.25, u[loop == k], percent[loop == k]) for k in range(3)]
    assert max(at_quarter) - min(at_quarter) < 1.0


def test_empty_run_writes_nothing():
    reader = MagicMock()
    reader.read_frame.return_value = pd.DataFrame(
        columns=["time", "lattitude", "longitude"]
    )
    writer = MagicMock()
    LapProgressStep(reader=reader, writer=writer).run(RunContext(run_id="run-1"))

    assert writer.delete_for_run.call_count == 2
    writer.append.assert_not_called()


# Distances along a 100 m ideal lap -> percentages, all one lap unless noted.
@pytest.mark.parametrize(
    ("s", "expected"),
    [
        # Starts just before the gate: reads 0, not 99.5.
        ([99.5, 0.5, 50.0, 99.0], [0.0, 0.5, 50.0, 99.0]),
        # Never goes backwards.
        ([30.0, 20.0], [30.0, 30.0]),
        # Ends just past the gate: reads 100, not 0.5.
        ([2.0, 50.0, 97.0, 0.5, 1.5], [2.0, 50.0, 97.0, 100.0, 100.0]),
        # Two loops merged into one lap: wraps back to 0 at the gate.
        ([10.0, 40.0, 70.0, 95.0, 5.0, 40.0], [10.0, 40.0, 70.0, 95.0, 5.0, 40.0]),
        # Off-track points stay empty.
        ([10.0, np.nan, 20.0], [10.0, np.nan, 20.0]),
    ],
)
def test_lap_percentages(s, expected):
    s = np.array(s)
    percent = lap_percentages(s, np.ones(len(s), dtype=np.int64), 100.0, 5.0)
    assert percent.tolist() == pytest.approx(expected, nan_ok=True)
