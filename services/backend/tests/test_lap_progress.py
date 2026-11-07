from datetime import datetime, timedelta

import numpy as np
import pytest

from orion_backend.lap_progress import lap_progress, reference_lap
from orion_core.geometry import EARTH_RADIUS_M
from orion_core.models.orion import Lap

START = datetime(2026, 1, 1, 12, 0, 0)
ORIGIN_LAT, ORIGIN_LON = 42.34, -71.09


def lat_lon(x_m: list[float], y_m: list[float]) -> tuple[np.ndarray, np.ndarray]:
    """Meters east (x) and north (y) of the origin, as latitude/longitude."""
    lat = ORIGIN_LAT + np.degrees(np.asarray(y_m) / EARTH_RADIUS_M)
    lon = ORIGIN_LON + np.degrees(
        np.asarray(x_m) / (EARTH_RADIUS_M * np.cos(np.radians(ORIGIN_LAT)))
    )
    return lat, lon


# The reference drives 100 m north from the origin.
REF = lat_lon([0.0] * 101, list(range(101)))


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


def test_lap_progress_matches_points_off_the_reference_line():
    progress = lap_progress(*lat_lon([2, -2, 2, 2], [0, 25, 50, 100]), *REF)
    assert progress == pytest.approx([0, 0.25, 0.5, 1], abs=0.01)


def test_lap_progress_of_a_lap_starting_partway():
    progress = lap_progress(*lat_lon([0, 0], [50, 75]), *REF)
    assert progress == pytest.approx([0.5, 0.75], abs=0.01)
