from datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.lap_step.lap_constants import EARTH_RADIUS_M
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


def run_lap_step(track: pd.DataFrame, page_size: int) -> pd.DataFrame:
    """Drive LapStep like the base class's `run`, without a database."""
    reader = MagicMock()
    reader.read_frame.return_value = pd.DataFrame([[track["time"].max()]])
    step = LapStep(reader=reader, writer=MagicMock())
    ctx = RunContext(run_id="run-1")

    step.prepare(ctx)
    pages = [track.iloc[i : i + page_size] for i in range(0, len(track), page_size)]
    laps = [step.transform(page.reset_index(drop=True), ctx) for page in pages]
    return pd.concat([lap for lap in laps if not lap.empty], ignore_index=True)


def assert_laps_cover_run(laps: pd.DataFrame, track: pd.DataFrame) -> None:
    assert laps["lap_id"].tolist() == list(range(1, len(laps) + 1))
    assert laps["start_time"].iloc[0] == track["time"].iloc[0]
    assert laps["end_time"].iloc[-1] == track["time"].iloc[-1]
    # Each lap starts exactly where the previous one ended: no gaps, no overlaps.
    assert laps["start_time"].iloc[1:].tolist() == laps["end_time"].iloc[:-1].tolist()


@pytest.mark.parametrize("page_size", [10_000, 300, 301, 7])
def test_circle_driven_three_times_gives_three_laps(page_size):
    # Stop just short of the line, so the run's end isn't also a crossing.
    track = circle(loops=2.95)
    laps = run_lap_step(track, page_size)

    assert len(laps) == 3
    assert_laps_cover_run(laps, track)
    lap_times = (laps["end_time"] - laps["start_time"]).dt.total_seconds()
    assert lap_times.iloc[:2].tolist() == pytest.approx([30.0, 30.0], abs=0.2)


def test_page_size_does_not_change_laps():
    track = circle(loops=2.95)
    expected = run_lap_step(track, 10_000)
    for page_size in (300, 301, 299, 7):
        pd.testing.assert_frame_equal(run_lap_step(track, page_size), expected)


def test_run_ending_on_a_crossing_has_no_empty_lap():
    # Three loops plus one point, with the point on the line removed, so the
    # run's last point is the first point past the gate.
    track = circle(loops=3 + 1 / 300).drop(index=900).reset_index(drop=True)
    laps = run_lap_step(track, 300)

    assert len(laps) == 3
    assert_laps_cover_run(laps, track)
    assert (laps["end_time"] > laps["start_time"]).all()


def test_straight_line_gives_one_lap():
    x = np.linspace(0, 500, 600)
    track = track_frame(x, np.zeros_like(x))
    laps = run_lap_step(track, 100)

    assert len(laps) == 1
    assert_laps_cover_run(laps, track)


def test_ctx_records_gate_once_found():
    track = circle(loops=1.5)
    reader = MagicMock()
    reader.read_frame.return_value = pd.DataFrame([[track["time"].max()]])
    step = LapStep(reader=reader, writer=MagicMock())
    ctx = RunContext(run_id="run-1")
    step.prepare(ctx)

    step.transform(track.iloc[:200], ctx)
    assert ctx.found_gate is False
    step.transform(track.iloc[200:].reset_index(drop=True), ctx)
    assert ctx.found_gate is True
