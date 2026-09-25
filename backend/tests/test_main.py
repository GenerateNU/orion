from unittest.mock import Mock

from main import health
from services.race_service import RaceService


def test_health_returns_ok_status():
    assert health() == {"status": "ok"}


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