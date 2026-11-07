from datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from orion_core.geometry import EARTH_RADIUS_M
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.lap_step.lap_step import LapStep

ORIGIN_LAT, ORIGIN_LON = 42.34, -71.09
START = datetime(2026, 1, 1, 12, 0, 0)
# 10 Hz, so each point is 0.1 s after the last.
POINTS_PER_SECOND = 10


def track_frame(x: np.ndarray, y: np.ndarray) -> pd.DataFrame:
    """estimated_car_state rows for a path given in local x/y meters."""
    lat = ORIGIN_LAT + np.degrees(y / EARTH_RADIUS_M)
    lon = ORIGIN_LON + np.degrees(x / (EARTH_RADIUS_M * np.cos(np.radians(ORIGIN_LAT))))
    time = pd.date_range(START, periods=len(x), freq=f"{1000 // POINTS_PER_SECOND}ms")
    return pd.DataFrame({"time": time, "lattitude": lat, "longitude": lon})


def circle(loops: float, radius_m: float = 50.0, points_per_loop: int = 300):
    """A circle starting at (0, 0) heading +x, driven `loops` times."""
    theta = np.linspace(0, 2 * np.pi * loops, round(points_per_loop * loops) + 1)
    return track_frame(radius_m * np.sin(theta), radius_m * (1 - np.cos(theta)))


def run_lap_step(track: pd.DataFrame, **ctx_overrides) -> MagicMock:
    """Run LapStep on `track` without a database, and return its mock writer.

    `ctx_overrides` replace RunContext fields, e.g. the `lap_*` tunables.
    """
    reader = MagicMock()
    reader.read_frame.return_value = track
    writer = MagicMock()
    ctx = RunContext(run_id="run-1", **ctx_overrides)
    LapStep(reader=reader, writer=writer).run(ctx)
    return writer


def lap_rows(track: pd.DataFrame, **ctx_overrides) -> pd.DataFrame:
    """The laps LapStep writes for `track`, which it writes in one append."""
    writer = run_lap_step(track, **ctx_overrides)
    writer.append.assert_called_once()
    table, laps = writer.append.call_args.args
    assert table == "laps"
    assert isinstance(laps, pd.DataFrame)
    return laps


def assert_laps_cover_run(laps: pd.DataFrame, track: pd.DataFrame) -> None:
    assert laps["lap_id"].tolist() == list(range(1, len(laps) + 1))
    assert laps["start_time"].iloc[0] == track["time"].iloc[0]
    assert laps["end_time"].iloc[-1] == track["time"].iloc[-1]
    # Each lap starts exactly where the previous one ended: no gaps, no overlaps.
    assert laps["start_time"].iloc[1:].tolist() == laps["end_time"].iloc[:-1].tolist()


def test_circle_driven_three_times_gives_three_laps():
    # Stop just short of the line, so the run's end isn't also a crossing.
    track = circle(loops=2.95)
    laps = lap_rows(track)

    assert len(laps) == 3
    assert_laps_cover_run(laps, track)
    lap_times = (laps["end_time"] - laps["start_time"]).dt.total_seconds()
    assert lap_times.iloc[:2].tolist() == pytest.approx([30.0, 30.0], abs=0.2)


def test_run_ending_on_a_crossing_has_no_empty_lap():
    # Three loops plus one point, with the point on the line removed, so the
    # run's last point is the first point past the gate.
    track = circle(loops=3 + 1 / 300).drop(index=900).reset_index(drop=True)
    laps = lap_rows(track)

    assert len(laps) == 3
    assert_laps_cover_run(laps, track)
    assert (laps["end_time"] > laps["start_time"]).all()


def test_tunables_come_from_the_run_context():
    # Each loop takes 30 s, so a 40 s minimum lap time drops every other crossing.
    track = circle(loops=4.95)
    laps = lap_rows(track, lap_min_lap_time_s=40.0)

    assert len(laps) == 3
    assert_laps_cover_run(laps, track)
    lap_times = (laps["end_time"] - laps["start_time"]).dt.total_seconds()
    assert lap_times.iloc[:2].tolist() == pytest.approx([60.0, 60.0], abs=0.2)


def test_reads_the_run_in_one_query():
    track = circle(loops=1.5)
    reader = MagicMock()
    reader.read_frame.return_value = track
    LapStep(reader=reader, writer=MagicMock()).run(RunContext(run_id="run-1"))

    reader.read_frame.assert_called_once()


def test_straight_line_gives_one_lap():
    x = np.linspace(0, 500, 600)
    track = track_frame(x, np.zeros_like(x))
    laps = lap_rows(track)

    assert len(laps) == 1
    assert_laps_cover_run(laps, track)


def test_empty_run_writes_nothing():
    writer = run_lap_step(track_frame(np.empty(0), np.empty(0)))

    writer.delete_for_run.assert_called_once_with("laps", "run-1")
    writer.append.assert_not_called()
