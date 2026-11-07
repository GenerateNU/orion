from datetime import datetime, timedelta

from orion_backend.lap_progress import reference_lap
from orion_core.models.orion import Lap

START = datetime(2026, 1, 1, 12, 0, 0)


def laps(*seconds: float) -> list[Lap]:
    """Back-to-back laps with the given lap times, numbered from 1."""
    rows, start = [], START
    for lap_id, length in enumerate(seconds, start=1):
        end = start + timedelta(seconds=length)
        rows.append(Lap(run_id="run-1", lap_id=lap_id, start_time=start, end_time=end))
        start = end
    return rows


def test_reference_lap_is_the_median_by_lap_time():
    assert reference_lap(laps(400, 30, 95, 100, 90)).lap_id == 3


def test_reference_lap_of_two_middle_laps_has_the_lower_lap_id():
    assert reference_lap(laps(30, 100, 90, 400)).lap_id == 2


def test_reference_lap_of_one_lap_is_itself():
    assert reference_lap(laps(60)).lap_id == 1
