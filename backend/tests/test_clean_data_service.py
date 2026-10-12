
"""Unit tests for OrionService.
 
These use fake Penelope and repository objects instead of real databases, so
they run anywhere (including CI) and never read or write real data.
"""
 
import logging
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
 
import numpy as np
import pytest
 
from orion.service import (
    DEFAULT_GPS_LAG_SECONDS,
    INVESTIGATION_NAMES,
    NAME_TO_UNIT,
    TAG_TO_NAME,
    OrionService,
)
 
RUN_ID = "test-run"
T = datetime(2026, 8, 15, 18, 17, 3, tzinfo=UTC)
LAG = timedelta(seconds=DEFAULT_GPS_LAG_SECONDS)
 
# Real catalog tags covering each case: multi-value, GPS, and single-value
ACCEL_TAG = "VCU_Ethernet/A/Acceleration"
GPS_TAG = "TPU/GPS/Location"
SPEED_TAG = "VCU/CarState/speed"
ACCEL = TAG_TO_NAME[ACCEL_TAG]
GPS = TAG_TO_NAME[GPS_TAG]
SPEED = TAG_TO_NAME[SPEED_TAG]
 
 
def make_chunk(rows):
    """Build a chunk shaped like PenelopeClient's output: a 2D object array
    with columns [time, dataTypeName, runId, values]. Filled cell by cell so
    NumPy doesn't try to merge the value lists into an extra dimension."""
    arr = np.empty((len(rows), 4), dtype=object)
    for i, row in enumerate(rows):
        for j, item in enumerate(row):
            arr[i, j] = item
    return arr

class FakePenelope:
    """Stands in for PenelopeClient: yields the chunks it was given."""
 
    def __init__(self, chunks):
        self.chunks = chunks
 
    def get_by_run_id_and_time(self, run_id, start, end, raw_tags):
        yield from self.chunks
 
 
class FakeRepo:
    """Stands in for DataPointRepository: records every write, in order."""
 
    def __init__(self):
        self.calls = []        # (method name, rows, conn)
        self.conn = object()   # the "connection" begin() hands out
 
    @contextmanager
    def begin(self):
        yield self.conn
 
    def write_sensors(self, rows, conn=None):
        self.calls.append(("write_sensors", rows, conn))
        return len(rows)
 
    def write_sensor_sources(self, rows, conn=None):
        self.calls.append(("write_sensor_sources", rows, conn))
        return len(rows)
 
    def write_cleaned(self, rows, conn=None):
        self.calls.append(("write_cleaned", rows, conn))
        return len(rows)

def make_service():
    return OrionService(FakePenelope([]), FakeRepo())
 
def run_service(chunks):
    repo = FakeRepo()
    df = OrionService(FakePenelope(chunks), repo).clean_data(RUN_ID, T, T + timedelta(minutes=2))
    return df, repo
 
 
def test_clean_chunk_renames_splits_and_shifts_gps():
    chunk = make_chunk([
        (T, ACCEL_TAG, RUN_ID, [-870.0, -24.6, 486.0]),
        (T, GPS_TAG, RUN_ID, [42.33, -71.09]),
        (T, SPEED_TAG, RUN_ID, [42]),
    ])
    df = make_service()._clean_chunk(chunk)
    by_sensor = {r.sensor: (r.time, r.value) for r in df.itertuples()}
 
    # multi-value arrays split into _0/_1/_2, single values keep the plain name
    assert set(by_sensor) == {f"{ACCEL}_0", f"{ACCEL}_1", f"{ACCEL}_2", f"{GPS}_0", f"{GPS}_1", SPEED}
    assert not set(TAG_TO_NAME) & set(by_sensor)               # no raw tags
    assert by_sensor[SPEED] == (T, 42.0)                       # whole number -> float, not shifted
    assert by_sensor[f"{GPS}_0"][0] == T + LAG                 # GPS shifted by the lag
    assert set(df["runId"]) == {RUN_ID}
 
 
def test_clean_chunk_unknown_tag_raises():
    with pytest.raises(KeyError):
        make_service()._clean_chunk(make_chunk([(T, "NOT/A/REAL/TAG", RUN_ID, [1.0])])) 
 
def test_clean_data_writes_reference_tables_then_each_chunk():
    chunks = [
        make_chunk([(T, SPEED_TAG, RUN_ID, [1.0])]),
        make_chunk([(T + timedelta(seconds=1), SPEED_TAG, RUN_ID, [2.0])]),
    ]
    _, repo = run_service(chunks)
    names = [name for name, _, _ in repo.calls]
    writes = [rows for name, rows, _ in repo.calls if name == "write_cleaned"]
 
    # sensors before sensor_sources (foreign key), both before any readings
    assert names[:2] == ["write_sensors", "write_sensor_sources"]
    assert dict(repo.calls[0][1]) == NAME_TO_UNIT
    assert dict(repo.calls[1][1]) == TAG_TO_NAME
 
    assert len(writes) == 2                                    # one write per chunk
    assert list(writes[0][0]) == [RUN_ID, T, SPEED, 1.0]       # (runId, time, sensor, value)
    assert all(conn is repo.conn for _, _, conn in repo.calls)  # all in one transaction
 
 
def test_clean_data_adds_suffixed_sensors_once_and_returns_all_rows():
    chunks = [
        make_chunk([(T, ACCEL_TAG, RUN_ID, [1.0, 2.0, 3.0])]),
        make_chunk([(T + timedelta(seconds=1), ACCEL_TAG, RUN_ID, [4.0, 5.0, 6.0])]),
    ]
    df, repo = run_service(chunks)
 
    # write_sensors calls after the catalog one that actually added rows
    added = [rows for name, rows, _ in repo.calls[1:] if name == "write_sensors" and len(rows)]
    assert len(added) == 1                                     # second chunk adds nothing new
    assert dict(added[0]) == {f"{ACCEL}_{i}": NAME_TO_UNIT[ACCEL] for i in range(3)}
 
    assert {"time", "sensor", "value"} <= set(df.columns)
    assert len(df) == 6
    assert list(df.index) == list(range(6))                    # renumbered across chunks
 
 
def test_clean_data_flags_investigation_tags_once_per_run(caplog):
    if not INVESTIGATION_NAMES:
        pytest.skip("catalog has no NEEDS INVESTIGATION entries")
    name = min(INVESTIGATION_NAMES)
    tag = next(tag for tag, n in TAG_TO_NAME.items() if n == name)
    chunks = [make_chunk([(T + timedelta(seconds=i), tag, RUN_ID, [1.0])]) for i in range(2)]
 
    with caplog.at_level(logging.WARNING):
        run_service(chunks)
 
    assert caplog.text.count("NEEDS INVESTIGATION") == 1
    assert name in caplog.text