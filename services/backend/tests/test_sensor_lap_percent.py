import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from orion_backend.core.database import get_orion_db, get_penelope_db
from orion_backend.main import app
from orion_backend.repositories.lap_repository import LapRepository
from orion_backend.repositories.sensor_repository import SensorRepository
from orion_backend.services import sensor_service
from orion_backend.services.sensor_service import SensorService, attach_lap_progress

GPS = "TPU/GPS/Location"
OTHER = "BMS/Pack/SoC"
OFFSET = timedelta(seconds=2)
TOLERANCE = timedelta(milliseconds=50)
# OrionDB times are naive UTC; Penelope's are timezone-aware.
T0 = datetime(2026, 10, 1, 12, 0, 0)
START = T0.replace(tzinfo=UTC)
END = START + timedelta(minutes=1)

# Two laps: [T0, T0 + 10 s) and [T0 + 10 s, T0 + 20 s], the last one's end included.
LAPS = pd.DataFrame(
    {
        "lap_id": [1, 2],
        "start_time": [T0, T0 + timedelta(seconds=10)],
        "end_time": [T0 + timedelta(seconds=10), T0 + timedelta(seconds=20)],
    }
)


def ms(milliseconds: float) -> timedelta:
    return timedelta(milliseconds=milliseconds)


def positions(*rows: tuple[timedelta, float | None]) -> pd.DataFrame:
    return pd.DataFrame(
        [(T0 + at, percent) for at, percent in rows], columns=["time", "lap_percent"]
    )


# ---- attach_lap_progress ---------------------------------------------------------


def test_nearest_position_within_tolerance_gives_its_percent():
    track = positions((ms(0), 10.0), (ms(100), 11.0), (ms(200), 12.0))
    readings = [START + ms(40), START + ms(60), START + ms(190)]

    _, percents = attach_lap_progress(readings, track, LAPS, TOLERANCE)

    assert percents == [10.0, 11.0, 12.0]


def test_no_position_within_tolerance_gives_null():
    track = positions((ms(0), 10.0), (ms(1000), 20.0))
    readings = [START + ms(50), START + ms(51), START + ms(500)]

    _, percents = attach_lap_progress(readings, track, LAPS, TOLERANCE)

    # 50 ms away is still a match; 51 ms and 500 ms aren't.
    assert percents == [10.0, None, None]


def test_null_percent_stays_null():
    track = positions((ms(0), None), (ms(100), 30.0))
    _, percents = attach_lap_progress([START, START + ms(100)], track, LAPS, TOLERANCE)
    assert percents == [None, 30.0]


def test_readings_keep_their_order():
    track = positions((ms(0), 10.0), (ms(100), 11.0))
    _, percents = attach_lap_progress([START + ms(100), START], track, LAPS, TOLERANCE)
    assert percents == [11.0, 10.0]


@pytest.mark.parametrize(
    ("at", "lap_id"),
    [
        (timedelta(seconds=0), 1),  # a lap's start is in it
        (timedelta(seconds=10) - ms(1), 1),
        (timedelta(seconds=10), 2),  # a lap's end is the next lap's start
        (timedelta(seconds=20), 2),  # the last lap's end is in it
        (-ms(1), None),  # before the first lap
        (timedelta(seconds=20) + ms(1), None),  # after the last lap
    ],
)
def test_lap_id_at_lap_boundaries(at, lap_id):
    lap_ids, _ = attach_lap_progress([START + at], positions(), LAPS, TOLERANCE)
    assert lap_ids == [lap_id]


def test_naive_times_count_as_utc():
    track = positions((ms(0), 10.0))
    aware, _ = attach_lap_progress([START], track, LAPS, TOLERANCE)
    naive, percents = attach_lap_progress([T0], track, LAPS, TOLERANCE)
    assert aware == naive == [1]
    assert percents == [10.0]


def test_run_without_laps_or_positions_gives_nulls():
    empty_laps = LAPS.iloc[0:0]
    lap_ids, percents = attach_lap_progress([START], positions(), empty_laps, TOLERANCE)
    assert (lap_ids, percents) == ([None], [None])
    assert attach_lap_progress([], positions(), LAPS, TOLERANCE) == ([], [])


# ---- The service and route ----------------------------------------------------------


@pytest.fixture
def fake_dbs(monkeypatch):
    """Penelope returns one GPS and one SoC reading at START; OrionDB has a position
    at T0 + OFFSET (the GPS reading's corrected time) and one at T0, and the two
    laps. Returns the calls made to the lap repository."""
    settings = SimpleNamespace(
        gps_time_offset_s=OFFSET.total_seconds(), lap_percent_match_tolerance_s=0.05
    )
    monkeypatch.setattr(sensor_service, "get_settings", lambda: settings)
    calls: list[tuple[object, ...]] = []

    async def list_readings(self, *args):
        rows = [
            {"raw_tag": GPS, "time": START, "values": [1.0, 2.0]},
            {"raw_tag": OTHER, "time": START, "values": [80.0]},
        ]
        return [SimpleNamespace(_mapping=row) for row in rows]

    async def list_lap_percents(self, *args):
        calls.append(("lap_percents", *args))
        return [(T0, 5.0), (T0 + OFFSET, 25.0)]

    async def list_laps(self, *args):
        calls.append(("laps", *args))
        return list(LAPS.itertuples(index=False, name=None))

    async def find_lap_percent_times(self, *args):
        calls.append(("lap_percent_times", *args))
        # Only lap 1 has positions in the range, from T0 to T0 + 1 minute.
        return (T0, T0 + timedelta(minutes=1)) if args[1] == 1 else (None, None)

    monkeypatch.setattr(SensorRepository, "list_readings", list_readings)
    monkeypatch.setattr(LapRepository, "list_lap_percents", list_lap_percents)
    monkeypatch.setattr(LapRepository, "list_laps", list_laps)
    monkeypatch.setattr(LapRepository, "find_lap_percent_times", find_lap_percent_times)
    return calls


def get_data(**kwargs):
    service = SensorService(MagicMock(), MagicMock())
    return asyncio.run(
        service.get_sensor_data("run", [GPS, OTHER], START, END, **kwargs)
    )


def test_service_attaches_lap_progress_on_corrected_times(fake_dbs):
    response = get_data(with_lap_percent=True)

    # The GPS reading is shifted to START + OFFSET, so it matches that position.
    assert response.series[GPS].lap_percent == [25.0]
    assert response.series[OTHER].lap_percent == [5.0]
    assert response.series[GPS].lap_id == response.series[OTHER].lap_id == [1]
    # OrionDB is asked for the window in naive UTC, widened by the tolerance.
    assert fake_dbs[0] == ("lap_percents", "run", T0 - TOLERANCE, T0 + ms(60_050))
    assert fake_dbs[1] == ("laps", "run")


def test_service_without_the_flag_skips_oriondb(fake_dbs):
    response = get_data()

    assert fake_dbs == []
    assert response.series[GPS].lap_percent is None
    assert set(response.series[GPS].model_dump(exclude_unset=True)) == {
        "time",
        "values",
    }


def test_service_by_lap_percent_reads_that_window(fake_dbs):
    service = SensorService(MagicMock(), MagicMock())
    response = asyncio.run(
        service.get_sensor_data(
            "run", [GPS, OTHER], lap_id=1, start_percent=20.0, end_percent=40.0
        )
    )

    assert fake_dbs[0] == ("lap_percent_times", "run", 1, 20.0, 40.0)
    # OrionDB's naive UTC times come back timezone-aware, for Penelope.
    assert (response.start, response.end) == (START, END)
    assert response.series[GPS].values == [[1.0, 2.0]]


@pytest.fixture
def client(fake_dbs):
    app.dependency_overrides[get_penelope_db] = lambda: MagicMock()
    app.dependency_overrides[get_orion_db] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.clear()


def get(client, **params):
    query = {
        "sensors": f"{GPS},{OTHER}",
        "start": START.isoformat(),
        "end": END.isoformat(),
    }
    return client.get("/api/v1/runs/run/sensors/data", params={**query, **params})


def test_route_without_the_flag_returns_the_old_response(client):
    response = get(client)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"run_id", "start", "end", "series"}
    assert {name: set(series) for name, series in body["series"].items()} == {
        GPS: {"time", "values"},
        OTHER: {"time", "values"},
    }
    assert body["series"][GPS]["values"] == [[1.0, 2.0]]
    assert get(client, with_lap_percent="false").json() == body


def test_route_with_the_flag_adds_lap_id_and_lap_percent(client):
    response = get(client, with_lap_percent="true")

    assert response.status_code == 200
    gps = response.json()["series"][GPS]
    assert gps["lap_id"] == [1]
    assert gps["lap_percent"] == [25.0]
    assert len(gps["lap_id"]) == len(gps["lap_percent"]) == len(gps["time"])


def by_percent(client, **params):
    query = {
        "sensors": f"{GPS},{OTHER}",
        "lap_id": 1,
        "start_percent": 20,
        "end_percent": 40,
    }
    return client.get("/api/v1/runs/run/sensors/data", params={**query, **params})


def test_route_by_lap_percent(client):
    response = by_percent(client)

    assert response.status_code == 200
    assert response.json()["series"][GPS]["values"] == [[1.0, 2.0]]


@pytest.mark.parametrize(
    "params",
    [
        {"start_percent": None},  # part of the lap percent set
        {"start": START.isoformat(), "end": END.isoformat()},  # both sets
        {"start_percent": 50},  # start above end
    ],
)
def test_route_by_lap_percent_rejects_bad_sets(client, params):
    query = {
        "sensors": f"{GPS},{OTHER}",
        "lap_id": 1,
        "start_percent": 20,
        "end_percent": 40,
    }
    query = {k: v for k, v in {**query, **params}.items() if v is not None}
    response = client.get("/api/v1/runs/run/sensors/data", params=query)
    assert response.status_code == 422


def test_route_with_no_window_is_422(client):
    response = client.get("/api/v1/runs/run/sensors/data", params={"sensors": GPS})
    assert response.status_code == 422


def test_route_by_lap_percent_with_no_match_is_404(client):
    assert by_percent(client, lap_id=2).status_code == 404


def test_route_still_503s_without_penelope(fake_dbs):
    app.dependency_overrides[get_orion_db] = lambda: MagicMock()
    app.state.sessionmakers = {}
    try:
        response = get(TestClient(app), with_lap_percent="true")
    finally:
        app.dependency_overrides.clear()
        del app.state.sessionmakers
    assert response.status_code == 503


def test_new_fields_and_flag_show_in_the_openapi_docs(client):
    spec = client.get("/openapi.json").json()
    series = spec["components"]["schemas"]["SensorSeries"]["properties"]
    assert {"lap_id", "lap_percent"} <= set(series)
    params = spec["paths"]["/api/v1/runs/{run_id}/sensors/data"]["get"]["parameters"]
    assert "with_lap_percent" in {p["name"] for p in params}
