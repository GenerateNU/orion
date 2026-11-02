import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from orion_backend.services import sensor_service
from orion_backend.services.sensor_service import SensorService
from orion_core.db.sensor_catalog import lagged_raw_tags, lagged_sensors
from orion_core.queries.penelope_queries import select_readings_between
from orion_pipeline.steps.clean_step.clean_utils import shift_sensor_time

GPS = "TPU/GPS/Location"
OTHER = "BMS/Pack/SoC"
OFFSET = timedelta(seconds=2)
START = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
END = START + timedelta(minutes=1)


def test_catalog_flags_every_tpu_gps_sensor():
    assert lagged_raw_tags() == {
        f"TPU/GPS/{name}" for name in ("Altitude", "GroundSpeed", "Location", "Mode", "PPS")
    }


# Readings 1 µs inside and outside each edge, matched on corrected time for GPS.
@pytest.mark.parametrize(
    ("tag", "raw_time", "included"),
    [
        (GPS, START - OFFSET, True),
        (GPS, END - OFFSET, True),
        (GPS, START - OFFSET - timedelta(microseconds=1), False),
        (GPS, END - OFFSET + timedelta(microseconds=1), False),
        (OTHER, START, True),
        (OTHER, END, True),
        (OTHER, START - timedelta(microseconds=1), False),
        (OTHER, END + timedelta(microseconds=1), False),
    ],
)
def test_query_window_edges(tag, raw_time, included):
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE data (time, "dataTypeName", "runId", "values")'))
        conn.execute(
            text("INSERT INTO data VALUES (:t, :tag, 'run', NULL)"),
            {"t": raw_time.strftime("%Y-%m-%d %H:%M:%S.%f"), "tag": tag},
        )
        stmt = select_readings_between("run", [GPS, OTHER], START, END, {GPS}, OFFSET)
        assert len(conn.execute(stmt).all()) == int(included)


def get_data(monkeypatch, offset_s=OFFSET.total_seconds(), **kwargs):
    monkeypatch.setattr(
        sensor_service, "get_settings", lambda: SimpleNamespace(gps_time_offset_s=offset_s)
    )
    rows = [
        {"raw_tag": GPS, "time": START, "values": [1.0, 2.0]},
        {"raw_tag": OTHER, "time": START, "values": [80.0]},
    ]
    calls = []

    async def list_readings(*args):
        calls.append(args)
        return [SimpleNamespace(_mapping=row) for row in rows]

    service = SensorService(MagicMock())
    monkeypatch.setattr(service.repository, "list_readings", list_readings)
    response = asyncio.run(service.get_sensor_data("run", [GPS, OTHER], START, END, **kwargs))
    return response, calls[0]


def test_shifts_only_lagged_sensors(monkeypatch):
    response, args = get_data(monkeypatch)
    assert response.series[GPS].time == [START + OFFSET]
    assert response.series[OTHER].time == [START]
    assert args[-2:] == (lagged_raw_tags(), OFFSET)


@pytest.mark.parametrize(("offset_s", "kwargs"), [(2.0, {"gps_offset_on": False}), (0.0, {})])
def test_correction_can_be_turned_off(monkeypatch, offset_s, kwargs):
    response, args = get_data(monkeypatch, offset_s, **kwargs)
    assert response.series[GPS].time == [START]
    lagged, offset = args[-2:]
    assert not lagged or offset == timedelta(0)


def test_backend_matches_pipeline(monkeypatch):
    response, _ = get_data(monkeypatch)
    cleaned = shift_sensor_time(
        pd.DataFrame({"time": [START], "sensor": ["gps_location"]}),
        lagged_sensors(),
        OFFSET.total_seconds(),
    )
    assert cleaned["time"].iloc[0] == response.series[GPS].time[0]
