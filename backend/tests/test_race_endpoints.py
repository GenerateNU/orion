"""
The two OrionDB-wired endpoints, run for real against a throwaway in-memory database.

Only `races` and `estimated_positions` are created -- `data` uses a Postgres ARRAY
column that SQLite can't build, and these endpoints never touch it.
"""
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.pool import StaticPool

from main import app
from orion.db import get_connection
from orion.schema import estimated_positions_table, metadata, races_table

client = TestClient(app)


def sqlite_engine():
    # StaticPool keeps one connection so every request sees the same in-memory DB;
    # check_same_thread=False because FastAPI runs sync endpoints in a worker thread
    return create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


@pytest.fixture
def engine():
    engine = sqlite_engine()
    metadata.create_all(engine, tables=[races_table, estimated_positions_table])

    def test_connection() -> Iterator[Connection]:
        with engine.connect() as conn:
            yield conn

    app.dependency_overrides[get_connection] = test_connection
    yield engine
    app.dependency_overrides.clear()


def add_race(engine, race_id=1, name="Test Race", dates=date(2026, 5, 14)):
    with engine.begin() as conn:
        conn.execute(insert(races_table).values(race_id=race_id, name=name, dates=dates))


def add_positions(engine, race_id, lap_number, points):
    start = datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)
    with engine.begin() as conn:
        conn.execute(insert(estimated_positions_table), [
            {
                "race_id": race_id,
                "lap_number": lap_number,
                "timestamp": start + timedelta(seconds=i),
                "latitude": lat,
                "longitude": lon,
            }
            for i, (lat, lon) in enumerate(points)
        ])


# --- GET /api/races ---------------------------------------------------------

def test_races_empty_database_returns_empty_list(engine):
    """The ticket's main requirement: empty but live DB -> [] (RaceListView's EmptyState)."""
    response = client.get("/api/races")

    assert response.status_code == 200
    assert response.json() == []


def test_races_returns_rows_in_the_shape_the_frontend_reads(engine):
    add_race(engine, race_id=2, name="Second")
    add_race(engine, race_id=1, name="First")

    races = client.get("/api/races").json()

    # RaceListView reads race_id, name, dates
    assert [r["race_id"] for r in races] == [1, 2]
    assert races[0]["name"] == "First"
    assert races[0]["dates"] == "2026-05-14"


def test_races_filters_by_date(engine):
    add_race(engine, race_id=1, dates=date(2026, 5, 14))
    add_race(engine, race_id=2, dates=date(2026, 6, 1))

    races = client.get("/api/races?date=2026-06-01").json()

    assert [r["race_id"] for r in races] == [2]


def test_races_rejects_a_malformed_date(engine):
    assert client.get("/api/races?date=not-a-date").status_code == 422


# --- GET /api/races/{id}/laps/{lap}/positions ------------------------------

def test_positions_known_race_with_no_positions_returns_empty_list(engine):
    """The ticket's other main requirement: valid race, nothing yet -> [] (RaceMapView's EmptyState)."""
    add_race(engine, race_id=1)

    response = client.get("/api/races/1/laps/1/positions")

    assert response.status_code == 200
    assert response.json() == []


def test_positions_unknown_race_is_404(engine):
    response = client.get("/api/races/999/laps/1/positions")

    assert response.status_code == 404
    assert response.json()["detail"] == "Race 999 not found"


@pytest.mark.parametrize("url", [
    "/api/races/abc/laps/1/positions",  # race id not a number
    "/api/races/0/laps/1/positions",    # race ids start at 1
    "/api/races/-1/laps/1/positions",
    "/api/races/1/laps/x/positions",    # lap not a number
    "/api/races/1/laps/0/positions",    # laps start at 1
    "/api/races/1/laps/-1/positions",
    "/api/races/1/laps/1/positions?min_lat=abc",  # bad bounds
])
def test_positions_invalid_input_is_422(engine, url):
    add_race(engine, race_id=1)  # so a 422 can't be a disguised 404

    assert client.get(url).status_code == 422


def test_positions_returns_the_lap_in_time_order(engine):
    add_race(engine, race_id=1)
    add_positions(engine, 1, 1, [(42.34, -71.09), (42.35, -71.08), (42.36, -71.07)])
    add_positions(engine, 1, 2, [(10.0, 10.0)])  # a different lap, must not leak in

    positions = client.get("/api/races/1/laps/1/positions").json()

    # PositionMap reads latitude and longitude
    assert [(p["latitude"], p["longitude"]) for p in positions] == [
        (42.34, -71.09), (42.35, -71.08), (42.36, -71.07),
    ]
    assert set(positions[0]) == {"timestamp", "latitude", "longitude"}


def test_positions_bounding_box_filters(engine):
    add_race(engine, race_id=1)
    add_positions(engine, 1, 1, [(42.0, -71.0), (43.0, -72.0), (44.0, -73.0)])

    positions = client.get(
        "/api/races/1/laps/1/positions?min_lat=42.5&max_lat=43.5&min_lon=-72.5&max_lon=-71.5"
    ).json()

    assert [(p["latitude"], p["longitude"]) for p in positions] == [(43.0, -72.0)]


# --- stubs ------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "/api/races/1",
    "/api/races/1/laps",
    "/api/races/1/laps/1",
    "/api/races/1/laps/1/energy",
    "/api/races/1/laps/1/5?latitude=42.1&longitude=-71.1",
])
def test_stub_endpoints_respond_without_a_database(monkeypatch, url):
    """The ticket: endpoints not wired yet still return stub data and don't throw."""
    monkeypatch.delenv("NEON_DB_URL", raising=False)

    response = client.get(url)

    assert response.status_code == 200
    assert response.json()


def test_velocity_stub_requires_its_coordinates():
    """Missing required parameters are a 422, not a crash."""
    assert client.get("/api/races/1/laps/1/5").status_code == 422


# --- database problems ------------------------------------------------------

# SQLite reports a missing table as OperationalError, but Postgres (Neon) raises
# ProgrammingError for it, so these fake a connection that fails the way Postgres does.

def _failing_connection(error):
    conn = Mock()
    conn.execute.side_effect = error

    def test_connection() -> Iterator[Mock]:
        yield conn

    return test_connection


@pytest.mark.parametrize(("error", "status", "message"), [
    # table missing -- setup_orion.py hasn't run against this database yet
    (ProgrammingError("SELECT ...", {}, Exception('relation "races" does not exist')),
     500, "run setup_orion.py"),
    # connection dropped mid-query -- e.g. Neon autosuspended
    (OperationalError("SELECT ...", {}, Exception("server closed the connection")),
     503, "Lost connection to OrionDB"),
])
def test_database_errors_become_clear_responses(error, status, message):
    app.dependency_overrides[get_connection] = _failing_connection(error)
    try:
        response = client.get("/api/races")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status
    assert message in response.json()["detail"]
