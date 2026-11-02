"""Tests for BaseClient.read_all() method."""

import pytest
from sqlalchemy import Column, Float, String, create_engine, insert, select
from sqlalchemy.orm import DeclarativeBase

from orion_pipeline.clients.base_client import BaseClient


class Base(DeclarativeBase):
    pass


class SensorReading(Base):
    __tablename__ = "test_data"
    time = Column(String, primary_key=True)
    sensor = Column(String, primary_key=True)
    value = Column(Float)


@pytest.fixture(scope="function")
def engine():
    """Create in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Insert test data
    with engine.begin() as conn:
        conn.execute(
            insert(SensorReading).values(
                [
                    {"time": "2026-11-01T00:00:00", "sensor": "gps", "value": 1.5},
                    {"time": "2026-11-01T00:00:10", "sensor": "speed", "value": 25.0},
                    {"time": "2026-11-01T00:00:20", "sensor": "gps", "value": 2.5},
                    {"time": "2026-11-01T00:00:30", "sensor": "speed", "value": 26.0},
                ]
            )
        )

    yield engine


def test_read_all_returns_all_rows(engine):
    """read_all() should return all rows, not paginated."""
    client = BaseClient(engine, page_size=2)
    stmt = select(SensorReading)
    df = client.read_all(stmt, ("time", "sensor"))

    assert len(df) == 4
    assert list(df.columns) == ["time", "sensor", "value"]


def test_read_all_ordered_by_key(engine):
    """read_all() should order results by key columns."""
    client = BaseClient(engine, page_size=2)
    stmt = select(SensorReading)
    df = client.read_all(stmt, ("time", "sensor"))

    # Check ordered by time first, then sensor
    times = df["time"].tolist()
    assert times == sorted(times), "Not ordered by time"


def test_read_all_with_multiple_key_columns(engine):
    """read_all() should handle multiple key columns."""
    client = BaseClient(engine, page_size=2)
    stmt = select(SensorReading).order_by(None)  # Remove default ordering
    df = client.read_all(stmt, ("time", "sensor"))

    # Both time and sensor should be ordered
    assert len(df) == 4
    # Verify time is the primary sort
    assert df["time"].iloc[0] <= df["time"].iloc[-1]


def test_read_all_empty_result(engine):
    """read_all() should return empty DataFrame for no matches."""
    client = BaseClient(engine, page_size=2)
    stmt = select(SensorReading).where(SensorReading.sensor == "nonexistent")
    df = client.read_all(stmt, ("time", "sensor"))

    assert len(df) == 0
    assert list(df.columns) == ["time", "sensor", "value"]
