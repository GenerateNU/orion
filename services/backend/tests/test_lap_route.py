from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from orion_backend.core.database import get_orion_db
from orion_backend.main import app
from orion_backend.repositories.lap_repository import LapRepository

T0 = datetime(2026, 10, 1, 12, 0, 0)


@pytest.fixture
def client():
    app.dependency_overrides[get_orion_db] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_lists_the_runs_laps_in_order(client, monkeypatch):
    rows = [
        SimpleNamespace(
            lap_id=i,
            start_time=T0 + timedelta(seconds=60 * (i - 1)),
            end_time=T0 + timedelta(seconds=60 * i),
        )
        for i in (1, 2)
    ]
    monkeypatch.setattr(LapRepository, "list_laps", AsyncMock(return_value=rows))

    response = client.get("/api/v1/runs/run-1/laps")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": "run-1",
        "laps": [
            {
                "lap_id": 1,
                "start_time": "2026-10-01T12:00:00",
                "end_time": "2026-10-01T12:01:00",
            },
            {
                "lap_id": 2,
                "start_time": "2026-10-01T12:01:00",
                "end_time": "2026-10-01T12:02:00",
            },
        ],
    }


def test_a_run_with_no_laps_gives_an_empty_list(client, monkeypatch):
    monkeypatch.setattr(LapRepository, "list_laps", AsyncMock(return_value=[]))

    response = client.get("/api/v1/runs/unknown/laps")

    assert response.status_code == 200
    assert response.json() == {"run_id": "unknown", "laps": []}
