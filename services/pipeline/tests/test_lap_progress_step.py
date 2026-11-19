from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.lap_progress_step.ideal_lap import assign_lap_ids
from orion_pipeline.steps.lap_progress_step.lap_progress_step import LapProgressStep
from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (
    drop_forward_jumps,
    lap_percentages,
    match_to_ideal_lap,
    resample,
)
from orion_pipeline.steps.lap_step.lap_constants import EARTH_RADIUS_M
from orion_pipeline.steps.lap_step.lap_utils import headings, to_local_xy

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


def to_lat_lon(x, y, origin_lat, origin_lon):
    """Local x/y meters back to latitude/longitude (undoes `to_local_xy`)."""
    lat = origin_lat + np.degrees(y / EARTH_RADIUS_M)
    lon = origin_lon + np.degrees(x / (EARTH_RADIUS_M * np.cos(np.radians(origin_lat))))
    return lat, lon


def track_frame(x: np.ndarray, y: np.ndarray) -> pd.DataFrame:
    lat, lon = to_lat_lon(x, y, ORIGIN_LAT, ORIGIN_LON)
    time = START + pd.to_timedelta(np.arange(len(x)) * DT_S, unit="s")
    return pd.DataFrame({"time": time, "lattitude": lat, "longitude": lon})


def run_step(positions: pd.DataFrame, laps: pd.DataFrame, **ctx_overrides):
    """Run the step without a database.

    Returns (the frame written with `append`, or None if nothing was written;
    the writer mock).
    """
    reader = MagicMock()
    reader.read_frame.side_effect = [positions, laps]
    writer = MagicMock()
    ctx = RunContext(run_id="run-1", **ctx_overrides)
    LapProgressStep(reader=reader, writer=writer).run(ctx)
    if not writer.append.called:
        return None, writer
    return writer.append.call_args.args[1], writer


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
    progress, _ = run_step(positions, laps)

    assert list(progress.columns) == ["run_id", "time", "lap_id", "lap_percent"]
    assert (progress["run_id"] == "run-1").all()
    assert (
        progress["lap_id"].tolist() == assign_lap_ids(positions["time"], laps).tolist()
    )
    assert progress["lap_percent"].notna().all()
    grid = np.linspace(0.02, 0.98, 49)
    per_lap = np.array([percent_at(progress, u, lap, grid) for lap in laps["lap_id"]])
    spread = per_lap.max(axis=0) - per_lap.min(axis=0)
    assert spread.max() < 1.0
    # And it tracks distance around the track, not time.
    assert per_lap.mean(axis=0) == pytest.approx(100 * grid, abs=1.5)


def test_percentages_rise_through_each_lap_without_jumps():
    positions, laps, _ = drive(VARIED_LAPS, start_u=0.4, end_u=0.7)
    progress, _ = run_step(positions, laps)

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
    progress, _ = run_step(positions, laps)

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
    progress, _ = run_step(positions, laps)

    percent = progress["lap_percent"]
    far = detour & (30 * bump > 20)
    assert far.any()
    # NaN here; the client writes it as NULL (see test_oriondb_client.py).
    assert percent[far].isna().all()
    # Back on track afterwards, and everywhere off the detour.
    assert percent[~detour].notna().all()


def test_tunables_come_from_the_run_context():
    # Every point is "too slow", so none gets a percentage.
    positions, laps, _ = drive(VARIED_LAPS[:4])
    progress, _ = run_step(positions, laps, lap_progress_min_speed_mps=1000.0)

    assert progress["lap_percent"].isna().all()


def test_rerun_replaces_the_runs_rows():
    positions, laps, _ = drive(VARIED_LAPS[:4])
    _, writer = run_step(positions, laps)

    names = [c[0] for c in writer.method_calls]
    assert names == ["delete_for_run", "append"]
    writer.delete_for_run.assert_called_once_with("lap_progress", "run-1")
    assert writer.append.call_args.args[0] == "lap_progress"


def test_too_few_laps_writes_nothing():
    # With two laps, both are first or last laps, so no lap can be the ideal lap.
    positions, laps, _ = drive(VARIED_LAPS[:2])
    progress, writer = run_step(positions, laps)

    # An empty frame, which `append` skips: the run has no lap_progress rows.
    assert progress.empty
    writer.delete_for_run.assert_called_once()


def test_empty_run_writes_nothing():
    reader = MagicMock()
    reader.read_frame.return_value = pd.DataFrame(
        columns=["time", "lattitude", "longitude"]
    )
    writer = MagicMock()
    LapProgressStep(reader=reader, writer=writer).run(RunContext(run_id="run-1"))

    writer.delete_for_run.assert_called_once()
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


# ---- Bad matches ----------------------------------------------------------


def jump_guard(s, time_s):
    return drop_forward_jumps(
        np.array(s, dtype=float),
        np.array(time_s, dtype=float),
        100.0,
        max_speed_mps=10.0,
        jump_margin_m=2.0,
    )


def test_drop_forward_jumps_rejects_a_point_too_far_ahead():
    # 1 m per second; the 60 m point is far beyond 10 m/s * 1 s + 2 m.
    s = jump_guard([10, 11, 60, 13, 14], [0, 1, 2, 3, 4])
    assert s.tolist() == pytest.approx([10, 11, np.nan, 13, 14], nan_ok=True)


def test_drop_forward_jumps_compares_to_the_furthest_point_not_the_last():
    # The bad backward point (2 m) is kept, and the points after it aren't
    # treated as jumps from it.
    s = jump_guard([10, 11, 2, 13, 14], [0, 1, 2, 3, 4])
    assert s.tolist() == pytest.approx([10, 11, 2, 13, 14])


def test_drop_forward_jumps_allows_more_after_a_gap_and_across_the_gate():
    # 40 m ahead is fine after 5 s (10 m/s * 5 s + 2 m). 98 -> 3 m is 5 m
    # forward around the loop, not 95 m back.
    s = jump_guard([10, np.nan, 50, 98, 3], [0, 2, 5, 10, 11])
    assert s.tolist() == pytest.approx([10, np.nan, 50, 98, 3], nan_ok=True)


def move_point(positions, index, to_u):
    """Positions with point `index` moved onto the centerline at fraction `to_u`."""
    x, y = stadium(np.array([to_u]))
    lat, lon = to_lat_lon(x, y, ORIGIN_LAT, ORIGIN_LON)
    moved = positions.copy()
    moved.loc[index, ["lattitude", "longitude"]] = [lat[0], lon[0]]
    return moved


@pytest.mark.parametrize(
    ("at_u", "to_u"),
    [
        (0.02, 0.12),  # ~70 m ahead on the same straight
        (0.10, 0.00),  # ~70 m behind on the same straight
    ],
)
def test_one_bad_point_mid_lap_leaves_the_rest_of_the_lap_rising(at_u, to_u):
    positions, laps, u = drive(VARIED_LAPS)
    lap3 = assign_lap_ids(positions["time"], laps) == 3
    bad = int(np.flatnonzero(lap3 & (u >= at_u))[0])
    clean, _ = run_step(positions, laps)
    progress, _ = run_step(move_point(positions, bad, to_u), laps)

    # The bad point's neighbors take their heading from it, so they may be
    # rejected as heading the wrong way. Every other point is untouched.
    near_bad = np.abs(np.arange(len(u)) - bad) <= 1
    others = np.flatnonzero(lap3 & ~near_bad)
    got = progress["lap_percent"].to_numpy()[others]
    expected = clean["lap_percent"].to_numpy()[others]
    assert got == pytest.approx(expected, abs=0.1)
    assert (np.diff(got) >= 0).all()


# ---- Matching between ideal lap points --------------------------------------------


def match_all(x, y, ideal):
    hx, hy = headings(x, y)
    return match_to_ideal_lap(
        x,
        y,
        hx,
        hy,
        np.ones(len(x), dtype=bool),
        ideal,
        max_offtrack_m=15.0,
        min_heading_dot=0.5,
        heading_weight_m=10.0,
    )


def test_matching_is_continuous_between_ideal_lap_points():
    # Ideal lap points 2 m apart; positions every 0.1 m, 0.5 m off the line.
    line_x, line_y = stadium(np.linspace(0, 1, 2000, endpoint=False))
    ideal = resample(line_x, line_y, 2.0)
    u = np.linspace(0.1, 0.15, 300)
    x, y = stadium(u, 0.5)

    s = match_all(x, y, ideal)

    # On the straight, the distance follows the car, not the 2 m point spacing.
    assert s == pytest.approx(u * PERIMETER_M, abs=0.05)


@pytest.mark.parametrize("offset_m", [-4.0, 4.0])
def test_matching_rises_steadily_through_bends_off_the_line(offset_m):
    # Driving 4 m outside (and inside) the line all the way round, through both
    # bends: the distance never holds still or steps back.
    line_x, line_y = stadium(np.linspace(0, 1, 2000, endpoint=False))
    ideal = resample(line_x, line_y, 1.0)
    u = np.linspace(0.01, 0.99, 3000)
    x, y = stadium(u, offset_m)

    steps = np.diff(match_all(x, y, ideal))

    assert (steps > 0).all()
    assert steps.max() < 3 * steps.mean()
