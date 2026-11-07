import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from orion_backend.core.exceptions import NotFoundError
from orion_backend.services.lap_progress_service import LapProgressService
from orion_core.models.orion import Lap

START = datetime(2026, 1, 1, 12, 0, 0)
RADIUS_DEG = 0.00015


def at(seconds: float) -> datetime:
    return START + timedelta(seconds=seconds)


# Two 10 s laps around a circle on the equator, one point a second, ending back at
# the start: 21 points.
ROWS = [
    SimpleNamespace(
        time=at(s),
        lattitude=RADIUS_DEG * np.sin(2 * np.pi * s / 10),
        longitude=RADIUS_DEG * np.cos(2 * np.pi * s / 10),
    )
    for s in range(21)
]
LAPS = [
    Lap(run_id="run", lap_id=1, start_time=at(0), end_time=at(10)),
    Lap(run_id="run", lap_id=2, start_time=at(10), end_time=at(20)),
]


def get_lap_progress(monkeypatch, start, end, laps=LAPS, rows=ROWS):
    async def list_laps(run_id):
        return laps

    async def list_positions(run_id, start, end):
        return [row for row in rows if start <= row.time <= end]

    service = LapProgressService(MagicMock())
    monkeypatch.setattr(service.lap_repository, "list_laps", list_laps)
    monkeypatch.setattr(service.state_repository, "list_positions", list_positions)
    return asyncio.run(service.get_lap_progress("run", start, end))


def test_whole_run_has_progress_per_lap_without_the_last_point(monkeypatch):
    response = get_lap_progress(monkeypatch, at(0), at(20))
    assert response.time == [row.time for row in ROWS[:20]]
    assert response.progress == pytest.approx([s / 9 for s in range(10)] * 2, abs=0.01)


def test_window_inside_a_lap(monkeypatch):
    response = get_lap_progress(monkeypatch, at(12), at(14))
    assert response.progress == pytest.approx([2 / 9, 3 / 9, 4 / 9], abs=0.01)


def test_run_without_laps_is_not_found(monkeypatch):
    with pytest.raises(NotFoundError, match="Laps for run 'run' not found"):
        get_lap_progress(monkeypatch, at(0), at(20), laps=[])


def test_reference_lap_without_positions_is_not_found(monkeypatch):
    with pytest.raises(NotFoundError, match="Data for lap '1' not found"):
        get_lap_progress(monkeypatch, at(0), at(20), rows=[])
