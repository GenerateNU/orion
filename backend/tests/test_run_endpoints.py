"""
The two OrionDB-wired endpoints, run for real against a throwaway in-memory database.

Only `estimated_car_state` is created -- it's the only table these endpoints read,
and `data` uses a Postgres ARRAY column that SQLite can't build.
"""
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.pool import StaticPool

from main import app
from orion.connection import get_connection
from orion.schema import estimated_car_state_table, metadata

client = TestClient(app)

RUN_1 = UUID("11111111-1111-1111-1111-111111111111")
RUN_2 = UUID("22222222-2222-2222-2222-222222222222")
MISSING_RUN = UUID("99999999-9999-9999-9999-999999999999")


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
    metadata.create_all(engine, tables=[estimated_car_state_table])

    def test_connection() -> Iterator[Connection]:
        with engine.connect() as conn:
            yield conn

    app.dependency_overrides[get_connection] = test_connection
    yield engine
    app.dependency_overrides.clear()


def add_positions(engine, run_id, lap_id, points, start=datetime(2026, 5, 14, 12, tzinfo=UTC)):
    """Insert one car state per (lat, lon) point, 0.1 seconds apart. A run exists
    once it has rows here -- there is no separate runs table."""
    with engine.begin() as conn:
        conn.execute(insert(estimated_car_state_table), [
            {
                "runId": run_id,
                "lapId": lap_id,
                "time": start + timedelta(seconds=i * 0.1),
                "latitude": lat,
                "longitude": lon,
            }
            for i, (lat, lon) in enumerate(points)
        ])


# --- GET /api/runs ---------------------------------------------------------

def test_runs_empty_database_returns_empty_list(engine):
    """The ticket's main requirement: empty but live DB -> [] (RunListView's EmptyState)."""
    response = client.get("/api/runs")

    assert response.status_code == 200
    assert response.json() == []


def test_runs_lists_each_run_once_most_recent_first(engine):
    add_positions(engine, RUN_1, 1, [(42.0, -71.0), (42.1, -71.1)], start=datetime(2026, 5, 14, 12, tzinfo=UTC))
    add_positions(engine, RUN_2, 1, [(42.0, -71.0)], start=datetime(2026, 6, 1, 9, tzinfo=UTC))

    runs = client.get("/api/runs").json()

    # one object per run (not one per row), RunListView reads run_id
    assert runs == [{"run_id": str(RUN_2)}, {"run_id": str(RUN_1)}]


# --- GET /api/runs/{id}/positions ------------------------------------------

def test_run_positions_returns_every_lap_in_time_order(engine):
    add_positions(engine, RUN_1, 1, [(42.0, -71.0), (42.1, -71.1)])
    # a later lap, and points with no lap yet -- both belong to the run
    add_positions(engine, RUN_1, 2, [(43.0, -72.0)], start=datetime(2026, 5, 14, 13, tzinfo=UTC))
    add_positions(engine, RUN_1, None, [(44.0, -73.0)], start=datetime(2026, 5, 14, 14, tzinfo=UTC))
    add_positions(engine, RUN_2, 1, [(10.0, 10.0)])  # another run, must not leak in

    positions = client.get(f"/api/runs/{RUN_1}/positions").json()

    assert [(p["latitude"], p["longitude"]) for p in positions] == [
        (42.0, -71.0), (42.1, -71.1), (43.0, -72.0), (44.0, -73.0),
    ]


def test_run_positions_unknown_run_is_404(engine):
    response = client.get(f"/api/runs/{MISSING_RUN}/positions")

    assert response.status_code == 404
    assert response.json()["detail"] == f"Run {MISSING_RUN} not found"


def test_run_positions_malformed_id_is_422(engine):
    assert client.get("/api/runs/not-a-uuid/positions").status_code == 422


# --- GET /api/runs/{id}/laps/{lap}/positions ------------------------------

def test_lap_positions_unknown_run_is_404(engine):
    response = client.get(f"/api/runs/{MISSING_RUN}/laps/1/positions")

    assert response.status_code == 404
    assert response.json()["detail"] == f"Run {MISSING_RUN} not found"


def test_lap_positions_known_run_with_nothing_on_that_lap_is_404(engine):
    add_positions(engine, RUN_1, 2, [(42.0, -71.0)])

    response = client.get(f"/api/runs/{RUN_1}/laps/1/positions")

    assert response.status_code == 404
    assert response.json()["detail"] == f"Lap 1 not found for run {RUN_1}"


@pytest.mark.parametrize("url", [
    "/api/runs/not-a-uuid/laps/1/positions",  # run ids are UUIDs
    f"/api/runs/{RUN_1}/laps/x/positions",    # lap not a number
    f"/api/runs/{RUN_1}/laps/0/positions",    # laps start at 1
    f"/api/runs/{RUN_1}/laps/-1/positions",
])
def test_lap_positions_invalid_input_is_422(engine, url):
    add_positions(engine, RUN_1, 1, [(42.0, -71.0)])  # so a 422 can't be a disguised 404

    assert client.get(url).status_code == 422


def test_lap_positions_returns_the_lap_in_time_order(engine):
    add_positions(engine, RUN_1, 1, [(42.34, -71.09), (42.35, -71.08), (42.36, -71.07)])
    # a different lap, points with no lap yet, and another run -- none may leak in
    add_positions(engine, RUN_1, 2, [(10.0, 10.0)], start=datetime(2026, 5, 14, 13, tzinfo=UTC))
    add_positions(engine, RUN_1, None, [(20.0, 20.0)], start=datetime(2026, 5, 14, 14, tzinfo=UTC))
    add_positions(engine, RUN_2, 1, [(30.0, 30.0)])

    positions = client.get(f"/api/runs/{RUN_1}/laps/1/positions").json()

    # PositionMap reads latitude and longitude
    assert [(p["latitude"], p["longitude"]) for p in positions] == [
        (42.34, -71.09), (42.35, -71.08), (42.36, -71.07),
    ]


@pytest.mark.parametrize("url", [
    f"/api/runs/{RUN_1}/positions",
    f"/api/runs/{RUN_1}/laps/1/positions",
])
def test_positions_shape(engine, url):
    add_positions(engine, RUN_1, 1, [(42.34, -71.09)])

    position = client.get(url).json()[0]

    # time is relabelled to timestamp; estimated_car_state has no speed/orientation yet
    assert set(position) == {"timestamp", "latitude", "longitude"}
    # an ISO datetime string (SQLite drops the timezone, Postgres keeps it)
    assert position["timestamp"].startswith("2026-05-14T12:00:00")


# --- stubs ------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    f"/api/runs/{RUN_1}",
    f"/api/runs/{RUN_1}/laps",
    f"/api/runs/{RUN_1}/laps/1",
])
def test_stub_endpoints_respond_without_a_database(monkeypatch, url):
    """The ticket: endpoints not wired yet still return stub data and don't throw."""
    monkeypatch.delenv("NEON_DB_URL", raising=False)

    response = client.get(url)

    assert response.status_code == 200
    assert response.json()


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
    # table or column missing -- Neon doesn't match orion/schema.py
    (ProgrammingError("SELECT ...", {}, Exception('relation "estimated_car_state" does not exist')),
     500, "matches orion/schema.py"),
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
