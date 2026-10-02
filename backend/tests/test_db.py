from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from main import app
from orion.db import get_connection, get_engine
from orion.exceptions import OrionConfigError

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_engine():
    """get_engine caches its engine, so each test starts from a clean slate."""
    get_engine.cache_clear()
    yield
    get_engine.cache_clear()
    app.dependency_overrides.clear()


def test_health_db_ok_with_a_working_database():
    """Swap in an in-memory database, the same way later route tests will."""
    engine = create_engine("sqlite://")

    def test_connection() -> Iterator[Connection]:
        with engine.connect() as conn:
            yield conn

    app.dependency_overrides[get_connection] = test_connection

    response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


def test_health_db_500_when_not_configured(monkeypatch):
    monkeypatch.delenv("NEON_DB_URL", raising=False)

    response = client.get("/api/health/db")

    assert response.status_code == 500
    assert "NEON_DB_URL is not set" in response.json()["detail"]


def test_health_db_503_when_database_unreachable(monkeypatch):
    # nothing listens on port 1, so the connection is refused immediately
    monkeypatch.setenv("NEON_DB_URL", "postgresql://user:pw@127.0.0.1:1/orion")

    response = client.get("/api/health/db")

    assert response.status_code == 503
    assert "Could not connect to OrionDB" in response.json()["detail"]


def test_plain_health_still_works_without_a_database(monkeypatch):
    monkeypatch.delenv("NEON_DB_URL", raising=False)

    assert client.get("/api/health").json() == {"status": "ok"}


def test_get_engine_rejects_blank_url(monkeypatch):
    """dotenv sets blank keys, so blank has to be treated the same as missing."""
    monkeypatch.setenv("NEON_DB_URL", "")

    with pytest.raises(OrionConfigError):
        get_engine()


@pytest.mark.parametrize("url", [
    "postgresql://user:pw@host/orion",
    "postgres://user:pw@host/orion",
    "postgresql+psycopg2://user:pw@host/orion",
])
def test_get_engine_uses_psycopg2(monkeypatch, url):
    """Neon's plain postgresql:// URLs must not fall through to psycopg v3."""
    monkeypatch.setenv("NEON_DB_URL", url)

    assert get_engine().dialect.driver == "psycopg2"


def test_get_engine_reuses_one_engine(monkeypatch):
    monkeypatch.setenv("NEON_DB_URL", "postgresql://user:pw@127.0.0.1:1/orion")

    assert get_engine() is get_engine()
