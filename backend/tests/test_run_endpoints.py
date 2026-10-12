"""
The two OrionDB-wired endpoints, run for real against a throwaway in-memory database.

Only `runs` and `estimated_positions` are created -- `data` uses a Postgres ARRAY
column that SQLite can't build, and these endpoints never touch it.
"""
from collections.abc import Iterator
from datetime import date
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.pool import StaticPool

from main import app
from orion.connection import get_connection
from orion.schema import estimated_positions_table, metadata, runs_table

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
    metadata.create_all(engine, tables=[runs_table, estimated_positions_table])

    def test_connection() -> Iterator[Connection]:
        with engine.connect() as conn:
            yield conn

    app.dependency_overrides[get_connection] = test_connection
    yield engine
    app.dependency_overrides.clear()


def add_run(engine, run_id="run-1", name="Test Run", dates=date(2026, 5, 14)):
    with engine.begin() as conn:
        conn.execute(insert(runs_table).values(run_id=run_id, name=name, dates=dates))


def add_positions(engine, run_id, lap_number, points):
    """Insert one position per (lat, lon) point, 0.1 seconds apart like the stub."""
    with engine.begin() as conn:
        conn.execute(insert(estimated_positions_table), [
            {
                "run_id": run_id,
                "lap_number": lap_number,
                "timestamp": round(i * 0.1, 1),
                "latitude": lat,
                "longitude": lon,
                "orientation": 90.0,
                "speed": 40.0,
                "tangential_acceleration": 1.2,
                "centripetal_acceleration": 0.4,
            }
            for i, (lat, lon) in enumerate(points)
        ])


# --- GET /api/runs ---------------------------------------------------------

def test_runs_empty_database_returns_empty_list(engine):
    """The ticket's main requirement: empty but live DB -> [] (RunListView's EmptyState)."""
    response = client.get("/api/runs")

    assert response.status_code == 200
    assert response.json() == []


def test_runs_returns_rows_in_the_shape_the_frontend_reads(engine):
    add_run(engine, run_id="run-2", name="Second")
    add_run(engine, run_id="run-1", name="First")

    runs = client.get("/api/runs").json()

    # RunListView reads run_id, name, dates
    assert [r["run_id"] for r in runs] == ["run-1", "run-2"]
    assert runs[0]["name"] == "First"
    assert runs[0]["dates"] == "2026-05-14"


def test_runs_filters_by_date(engine):
    add_run(engine, run_id="run-1", dates=date(2026, 5, 14))
    add_run(engine, run_id="run-2", dates=date(2026, 6, 1))

    runs = client.get("/api/runs?date=2026-06-01").json()

    assert [r["run_id"] for r in runs] == ["run-2"]


def test_runs_rejects_a_malformed_date(engine):
    assert client.get("/api/runs?date=not-a-date").status_code == 422


# --- GET /api/runs/{id}/laps/{lap}/positions ------------------------------

def test_positions_known_run_with_no_positions_returns_empty_list(engine):
    """The ticket's other main requirement: valid run, nothing yet -> [] (RunMapView's EmptyState)."""
    add_run(engine, run_id="run-1")

    response = client.get("/api/runs/run-1/laps/1/positions")

    assert response.status_code == 200
    assert response.json() == []


def test_positions_unknown_run_is_404(engine):
    response = client.get("/api/runs/missing-run/laps/1/positions")

    assert response.status_code == 404
    assert response.json()["detail"] == "Run missing-run not found"


@pytest.mark.parametrize("url", [
    "/api/runs/run-1/laps/x/positions",    # lap not a number
    "/api/runs/run-1/laps/0/positions",    # laps start at 1
    "/api/runs/run-1/laps/-1/positions",
    "/api/runs/run-1/laps/1/positions?min_lat=abc",  # bad bounds
])
def test_positions_invalid_input_is_422(engine, url):
    add_run(engine, run_id="run-1")  # so a 422 can't be a disguised 404

    assert client.get(url).status_code == 422


def test_positions_returns_the_lap_in_time_order(engine):
    add_run(engine, run_id="run-1")
    add_positions(engine, "run-1", 1, [(42.34, -71.09), (42.35, -71.08), (42.36, -71.07)])
    add_positions(engine, "run-1", 2, [(10.0, 10.0)])  # a different lap, must not leak in

    positions = client.get("/api/runs/run-1/laps/1/positions").json()

    # PositionMap reads latitude and longitude
    assert [(p["latitude"], p["longitude"]) for p in positions] == [
        (42.34, -71.09), (42.35, -71.08), (42.36, -71.07),
    ]


def test_positions_bounding_box_filters(engine):
    add_run(engine, run_id="run-1")
    add_positions(engine, "run-1", 1, [(42.0, -71.0), (43.0, -72.0), (44.0, -73.0)])

    positions = client.get(
        "/api/runs/run-1/laps/1/positions?min_lat=42.5&max_lat=43.5&min_lon=-72.5&max_lon=-71.5"
    ).json()

    assert [(p["latitude"], p["longitude"]) for p in positions] == [(43.0, -72.0)]


# --- stubs ------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "/api/runs/run-1",
    "/api/runs/run-1/laps",
    "/api/runs/run-1/laps/1",
    "/api/runs/run-1/laps/1/energy",
    "/api/runs/run-1/laps/1/5?latitude=42.1&longitude=-71.1",
])
def test_stub_endpoints_respond_without_a_database(monkeypatch, url):
    """The ticket: endpoints not wired yet still return stub data and don't throw."""
    monkeypatch.delenv("NEON_DB_URL", raising=False)

    response = client.get(url)

    assert response.status_code == 200
    assert response.json()


def test_velocity_stub_requires_its_coordinates():
    """Missing required parameters are a 422, not a crash."""
    assert client.get("/api/runs/run-1/laps/1/5").status_code == 422


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
    (ProgrammingError("SELECT ...", {}, Exception('relation "runs" does not exist')),
     500, "run setup_orion.py"),
    # connection dropped mid-query -- e.g. Neon autosuspended
    (OperationalError("SELECT ...", {}, Exception("server closed the connection")),
     503, "Lost connection to OrionDB"),
])
def test_database_errors_become_clear_responses(error, status, message):
    app.dependency_overrides[get_connection] = _failing_connection(error)
    try:
        response = client.get("/api/runs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status
    assert message in response.json()["detail"]

# Copied from the stubs the frontend was built against before this ticket.
STUB_RUN = {"run_id": "run-1", "name": "Northeastern Electric Racing", "dates": "2026-05-14"}
STUB_POSITION = {
    "timestamp": 0.0, "latitude": 40.7000, "longitude": -73.5000, "orientation": 90.0,
    "speed": 40.0, "tangential_acceleration": 1.2, "centripetal_acceleration": 0.4,
}

def shape(item):
    """The keys and value types of one JSON object, e.g. {"run_id": str, "name": str}."""
    return {key: type(value) for key, value in item.items()}


def test_runs_match_the_stub_shape(engine):
    add_run(engine)
    assert shape(client.get("/api/runs").json()[0]) == shape(STUB_RUN)


def test_positions_match_the_stub_shape(engine):
    add_run(engine)
    add_positions(engine, "run-1", 1, [(42.34, -71.09)])
    position = client.get("/api/runs/run-1/laps/1/positions").json()[0]
    assert shape(position) == shape(STUB_POSITION)
