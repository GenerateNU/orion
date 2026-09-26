from unittest.mock import Mock

from main import health
from services.race_service import RaceService


def test_health_returns_ok_status():
    assert health() == {"status": "ok"}


def test_get_races():
    repository = Mock()
    repository.get_races.return_value = [
        {"race_id": 1},
        {"race_id": 2}
    ]

    service = RaceService()
    service.repository = repository

    result = service.get_races()

    assert result == [
        {"race_id": 1},
        {"race_id": 2}
    ]


def test_get_races_with_date():
    repository = Mock()
    repository.get_races.return_value = [
        {"race_id": 1, "date": "2026-09-25"}
    ]

    service = RaceService()
    service.repository = repository

    result = service.get_races("2026-09-25")

    assert result == [
        {"race_id": 1, "date": "2026-09-25"}
    ]


def test_get_laps():
    repository = Mock()
    repository.get_laps.return_value = [
        {"lap_number": 1},
        {"lap_number": 2}
    ]

    service = RaceService()
    service.repository = repository

    result = service.get_laps(1)

    assert result == [
        {"lap_number": 1},
        {"lap_number": 2}
    ]


def test_get_specific_lap():
    repository = Mock()

    repository.get_lap.return_value = {
        "race_id": 1,
        "lap_number": 3
    }

    repository.get_positions.return_value = [
        {"speed": 10},
        {"speed": 20},
        {"speed": 30}
    ]

    service = RaceService()
    service.repository = repository

    result = service.get_specific_lap(1, 3)

    assert result["race_id"] == 1
    assert result["lap_number"] == 3
    assert result["average_speed"] == 20
    assert result["positions"] == [
        {"speed": 10},
        {"speed": 20},
        {"speed": 30}
    ]


def test_get_specific_lap_no_positions():
    repository = Mock()

    repository.get_lap.return_value = {
        "race_id": 1,
        "lap_number": 3
    }

    repository.get_positions.return_value = []

    service = RaceService()
    service.repository = repository

    result = service.get_specific_lap(1, 3)

    assert result["average_speed"] is None
    assert result["positions"] == []


def test_get_positions():
    repository = Mock()
    repository.get_positions.return_value = [
        {"latitude": 42.1, "longitude": -71.1}
    ]

    service = RaceService()
    service.repository = repository

    result = service.get_positions(1, 3)

    assert result == [
        {"latitude": 42.1, "longitude": -71.1}
    ]


def test_get_positions_with_bounds():
    repository = Mock()
    repository.get_positions.return_value = [
        {"latitude": 42.1, "longitude": -71.1}
    ]

    service = RaceService()
    service.repository = repository

    result = service.get_positions(
        1,
        3,
        42.0,
        43.0,
        -72.0,
        -71.0
    )

    assert result == [
        {"latitude": 42.1, "longitude": -71.1}
    ]


def test_get_lap_energy():
    repository = Mock()
    repository.get_lap_energy.return_value = {
        "energy_consumed": 125.5
    }

    service = RaceService()
    service.repository = repository

    result = service.get_lap_energy(1, 3)

    assert result == {
        "energy_consumed": 125.5
    }


def test_get_velocity_at_position():
    repository = Mock()
    repository.get_velocity_at_position.return_value = {
        "velocity": 25.5
    }

    service = RaceService()
    service.repository = repository

    result = service.get_velocity_at_position(
        1,
        3,
        42.1,
        -71.1
    )

    assert result == {
        "velocity": 25.5
    }


def test_get_specific_race():
    repository = Mock()
    repository.get_specific_race.return_value = {
        "race_id": 1,
        "date": "2026-09-25"
    }

    service = RaceService()
    service.repository = repository

    result = service.get_specific_race(1)

    assert result == {
        "race_id": 1,
        "date": "2026-09-25"
    }
