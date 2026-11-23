import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from orion_backend.core.database import get_orion_db, get_penelope_db
from orion_backend.main import app
from orion_backend.repositories.lap_progress_repository import LapProgressRepository
from orion_backend.repositories.sensor_repository import SensorRepository
from orion_backend.services import sensor_service
from orion_backend.services.sensor_service import SensorService, nearest_values

GPS = "TPU/GPS/Location"
OTHER = "BMS/Pack/SoC"
OFFSET = timedelta(seconds=2)
# OrionDB times are naive UTC; Penelope's are timezone-aware.
T0 = datetime(2026, 10, 1, 12, 0, 0)
START = T0.replace(tzinfo=UTC)
END = START + timedelta(minutes=1)


def at(seconds: float) -> datetime:
    return START + timedelta(seconds=seconds)


# ---- nearest_values ----------------------------------------------------------------


def test_nearest_values_takes_the_nearest_known_time():
    known = [at(0), at(1), at(2)]
    times = [at(0.4), at(0.6), at(1.9)]
    assert nearest_values(times, known, [10.0, 20.0, 30.0]) == [10.0, 20.0, 30.0]


def test_nearest_values_matches_however_far_away():
    known = [at(0), at(1)]
    times = [at(-60), at(60)]
    assert nearest_values(times, known, [10.0, 20.0]) == [10.0, 20.0]


def test_nearest_values_keeps_the_order_of_times():
    known = [at(0), at(1)]
    assert nearest_values([at(1), at(0)], known, [10.0, 20.0]) == [20.0, 10.0]


# ---- The service and routes ---------------------------------------------------------


@pytest.fixture
def fake_dbs(monkeypatch):
    """Penelope returns one GPS and one SoC reading at START. OrionDB has three
    positions for lap 1 only, at T0, T0 + OFFSET (the GPS reading's corrected time)
    and T0 + 1 minute. Returns the calls made to each database."""
    settings = SimpleNamespace(gps_time_offset_s=OFFSET.total_seconds())
    monkeypatch.setattr(sensor_service, "get_settings", lambda: settings)
    calls: dict[str, list[tuple[object, ...]]] = {"orion": [], "penelope": []}

    async def list_readings(self, *args):
        calls["penelope"].append(args)
        rows = [
            {"raw_tag": GPS, "time": START, "values": [1.0, 2.0]},
            {"raw_tag": OTHER, "time": START, "values": [80.0]},
        ]
        return [SimpleNamespace(_mapping=row) for row in rows]

    async def list_lap_percents(self, *args):
        calls["orion"].append(args)
        rows = [(T0, 5.0), (T0 + OFFSET, 25.0), (T0 + timedelta(minutes=1), 30.0)]
        return [
            SimpleNamespace(lap_id=1, time=time, lap_percent=percent)
            for time, percent in rows
        ]

    monkeypatch.setattr(SensorRepository, "list_readings", list_readings)
    monkeypatch.setattr(LapProgressRepository, "list_lap_percents", list_lap_percents)
    return calls


def test_service_matches_readings_to_positions_on_corrected_times(fake_dbs):
    service = SensorService(MagicMock(), MagicMock())
    [response] = asyncio.run(
        service.get_lap_sensor_data("run", [GPS, OTHER], [1], 20.0, 40.0)
    )

    assert fake_dbs["orion"] == [("run", [1], 20.0, 40.0)]
    # The window is the lap's first and last position, timezone-aware for Penelope.
    assert (response.lap_id, response.start, response.end) == (1, START, END)
    assert fake_dbs["penelope"][0][2:4] == (START, END)
    # The GPS reading is shifted to START + OFFSET, so it matches that position.
    assert response.series[GPS].lap_percent == [25.0]
    assert response.series[OTHER].lap_percent == [5.0]


@pytest.fixture
def client(fake_dbs):
    app.dependency_overrides[get_penelope_db] = lambda: MagicMock()
    app.dependency_overrides[get_orion_db] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_time_route_returns_the_old_response(client):
    params = {"sensors": f"{GPS},{OTHER}", "start": START.isoformat(), "end": END}
    response = client.get("/api/v1/runs/run/sensors/data", params=params)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"run_id", "start", "end", "series"}
    assert {name: set(series) for name, series in body["series"].items()} == {
        GPS: {"time", "values"},
        OTHER: {"time", "values"},
    }


def by_percent(client, **params):
    query = {
        "sensors": f"{GPS},{OTHER}",
        "lap_ids": [1, 1],
        "start_percent": 20,
        "end_percent": 40,
    }
    return client.get("/api/v1/runs/run/laps/sensors/data", params={**query, **params})


def test_lap_route_returns_one_response_per_lap_from_one_query(client, fake_dbs):
    response = by_percent(client)

    assert response.status_code == 200
    body = response.json()
    assert [lap["lap_id"] for lap in body] == [1, 1]
    gps = body[0]["series"][GPS]
    assert gps["values"] == [[1.0, 2.0]]
    assert gps["lap_percent"] == [25.0]
    assert len(fake_dbs["orion"]) == 1
    assert len(fake_dbs["penelope"]) == 2


@pytest.mark.parametrize(
    "params",
    [
        {"lap_ids": None},  # no laps
        {"lap_ids": "x"},  # not a lap id
        {"start_percent": 50},  # start above end
    ],
)
def test_lap_route_rejects_bad_parameters(client, params):
    query = {"sensors": GPS, "lap_ids": 1, "start_percent": 20, "end_percent": 40}
    query = {k: v for k, v in {**query, **params}.items() if v is not None}
    response = client.get("/api/v1/runs/run/laps/sensors/data", params=query)
    assert response.status_code == 422


def test_lap_route_gives_a_lap_without_positions_empty_series(client, fake_dbs):
    response = by_percent(client, lap_ids=[2, 1])

    assert response.status_code == 200
    empty, full = response.json()
    assert (empty["lap_id"], empty["start"], empty["end"]) == (2, None, None)
    assert empty["series"] == {
        GPS: {"time": [], "values": [], "lap_percent": []},
        OTHER: {"time": [], "values": [], "lap_percent": []},
    }
    assert full["series"][GPS]["lap_percent"] == [25.0]
    # Penelope is only asked about the lap that has positions.
    assert len(fake_dbs["penelope"]) == 1


def test_lap_route_with_no_lap_with_positions_is_404(client):
    assert by_percent(client, lap_ids=[2, 3]).status_code == 404


def test_lap_route_still_503s_without_penelope(fake_dbs):
    app.dependency_overrides[get_orion_db] = lambda: MagicMock()
    app.state.sessionmakers = {}
    try:
        response = by_percent(TestClient(app))
    finally:
        app.dependency_overrides.clear()
        del app.state.sessionmakers
    assert response.status_code == 503
