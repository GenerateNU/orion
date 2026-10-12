from unittest.mock import Mock

import pytest

from main import health
from backend.services.LapNotFoundError import LapNotFoundError
from backend.services.RunNotFoundError import RunNotFoundError

from services.run_service import RunService


def test_health_returns_ok_status():
    assert health() == {"status": "ok"}


def test_get_runs():
    repository = Mock()
    repository.get_runs.return_value = [
        {"run_id": 1},
        {"run_id": 2}
    ]

    service = RunService()
    service.repository = repository

    result = service.get_runs(Mock())

    assert result == [
        {"run_id": 1},
        {"run_id": 2}
    ]


def test_get_laps():
    repository = Mock()
    repository.get_laps.return_value = [
        {"lap_number": 1},
        {"lap_number": 2}
    ]

    service = RunService()
    service.repository = repository

    result = service.get_laps(1)

    assert result == [
        {"lap_number": 1},
        {"lap_number": 2}
    ]


def test_get_specific_lap():
    """Stub for now: hands back the repository's lap, without touching positions."""
    repository = Mock()

    repository.get_specific_lap.return_value = {
        "run_id": 1,
        "lap_number": 3,
        "average_speed": 45.2
    }

    service = RunService()
    service.repository = repository

    result = service.get_specific_lap(1, 3)

    assert result == {"run_id": 1, "lap_number": 3, "average_speed": 45.2}
    repository.get_specific_lap.assert_called_once_with(1, 3)
    repository.get_lap_positions.assert_not_called()


def test_get_run_positions():
    repository = Mock()
    repository.run_exists.return_value = True
    repository.get_run_positions.return_value = [
        {"latitude": 42.1, "longitude": -71.1}
    ]

    service = RunService()
    service.repository = repository

    result = service.get_run_positions(Mock(), 1)

    assert result == [
        {"latitude": 42.1, "longitude": -71.1}
    ]


def test_get_run_positions_unknown_run_raises():
    repository = Mock()
    repository.run_exists.return_value = False

    service = RunService()
    service.repository = repository

    with pytest.raises(RunNotFoundError):
        service.get_run_positions(Mock(), 999)

    # never queries positions for a run that doesn't exist
    repository.get_run_positions.assert_not_called()


def test_get_lap_positions():
    repository = Mock()
    repository.run_exists.return_value = True
    repository.lap_exists.return_value = True
    repository.get_lap_positions.return_value = [
        {"latitude": 42.1, "longitude": -71.1}
    ]

    service = RunService()
    service.repository = repository

    result = service.get_lap_positions(Mock(), 1, 3)

    assert result == [
        {"latitude": 42.1, "longitude": -71.1}
    ]


def test_get_lap_positions_unknown_run_raises():
    repository = Mock()
    repository.run_exists.return_value = False

    service = RunService()
    service.repository = repository

    with pytest.raises(RunNotFoundError):
        service.get_lap_positions(Mock(), 999, 1)

    repository.get_lap_positions.assert_not_called()


def test_get_lap_positions_unknown_lap_raises():
    repository = Mock()
    repository.run_exists.return_value = True
    repository.lap_exists.return_value = False

    service = RunService()
    service.repository = repository

    with pytest.raises(LapNotFoundError):
        service.get_lap_positions(Mock(), 1, 99)

    repository.get_lap_positions.assert_not_called()


def test_get_specific_run():
    repository = Mock()
    repository.get_specific_run.return_value = {
        "run_id": 1,
        "date": "2026-09-25"
    }

    service = RunService()
    service.repository = repository

    result = service.get_specific_run(1)

    assert result == {
        "run_id": 1,
        "date": "2026-09-25"
    }
