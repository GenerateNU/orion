from dotenv import load_dotenv; load_dotenv()
import logging
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, create_engine, func, or_, select

from orion.ingest import (
    DEFAULT_GPS_LAG_SECONDS,
    GPS_NAMES,
    TAG_TO_NAME,
    INVESTIGATION_NAMES,
    _clean_chunk,
    _delete_existing_rows,
    _flag_investigation_tags,
    _normalize_soc,
    _soc_scale,
    ingest_run,
    insert_cleaned_data,
)
from orion.schema import cleaned_data_table, sensor_sources_table, sensors_table
from penelope.client import PenelopeClient

logging.basicConfig(level=logging.INFO)

RUN_ID = "5eee6c81-e84d-4f08-b8c4-bc1a481a5ad6"
START = datetime(2026, 8, 15, 18, 17, tzinfo=UTC)
END = datetime(2026, 8, 15, 18, 19, tzinfo=UTC)
LAG = timedelta(seconds=DEFAULT_GPS_LAG_SECONDS)

penelope = PenelopeClient.from_env()
engine = create_engine(os.environ["NEON_DB_URL"])


# --- 1. SoC scale (read-only, Penelope only) ---
scale = _soc_scale(penelope, RUN_ID, START, END)
print("scale:", scale)
assert scale in (1.0, 100.0)
print("0.85 at scale 100 ->", _normalize_soc([0.85], 100.0))
assert _normalize_soc([0.85], 100.0) == [85.0]
assert _normalize_soc([85.0], 1.0) == [85.0]


# --- 2. NEEDS INVESTIGATION flagging (no database) ---
found = _flag_investigation_tags("test-run", {"bms_temp_avg", "gps_mode", "vcu_tsms"})
print("found:", found)
assert found == {"gps_mode", "vcu_tsms"}
assert _flag_investigation_tags("test-run", {"bms_temp_avg", "vcu_speed"}) == set()


# --- 3. _clean_chunk: rename, SoC, GPS shift, split (no database) ---
t = datetime(2026, 8, 15, 18, 17, 3, tzinfo=UTC)
chunk = [
    (t, "VCU_Ethernet/A/Acceleration", "run", [-870.0, -24.6, 486.0]),
    (t, "BMS/Pack/SoC", "run", [0.637]),
    (t, "VCU/CarState/speed", "run", [42]),          # whole number: should come out as a float
    (t, "TPU/GPS/Location", "run", [42.33, -71.09]),
]
rows = _clean_chunk(chunk, 100.0)
for row in rows:
    print(row)

by_sensor = {sensor: (time, value) for time, sensor, value in rows}
accel = TAG_TO_NAME["VCU_Ethernet/A/Acceleration"]
gps = TAG_TO_NAME["TPU/GPS/Location"]
soc = TAG_TO_NAME["BMS/Pack/SoC"]
assert {f"{accel}_0", f"{accel}_1", f"{accel}_2"} <= by_sensor.keys()   # 3-element array split
assert {f"{gps}_0", f"{gps}_1"} <= by_sensor.keys()                      # 2-element array split
assert accel not in by_sensor and gps not in by_sensor                   # no unsuffixed multi-value names
assert abs(by_sensor[soc][1] - 63.7) < 1e-9                              # SoC scaled
assert by_sensor[f"{gps}_0"][0] == t + LAG                               # GPS shifted
assert by_sensor[soc][0] == t                                            # non-GPS not shifted
assert all(isinstance(v, float) for _, _, v in rows)
assert not set(TAG_TO_NAME) & by_sensor.keys()                           # no raw tags

# An unknown tag should fail loudly, not be skipped
try:
    _clean_chunk([(t, "NOT/A/REAL/TAG", "run", [1.0])], 1.0)
    raise AssertionError("expected a KeyError for an unknown tag")
except KeyError:
    print("unknown tag raised KeyError as expected")


# --- 4. Delete + insert helpers inside a transaction that is rolled back ---
with engine.connect() as conn:
    trans = conn.begin()
    n = _delete_existing_rows(conn, RUN_ID, START, END)
    print("would delete:", n)

    fake_rows = [
        (datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC), "bms_pack_soc", 63.7),
        (datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC), "vcu_speed", 42.0),
    ]
    n = insert_cleaned_data(conn, "test-run", fake_rows)
    count = conn.execute(
        select(func.count()).select_from(cleaned_data_table)
        .where(cleaned_data_table.c.runId == "test-run")
    ).scalar()
    print("inserted:", n, "| in table:", count)
    assert n == count == 2
    assert insert_cleaned_data(conn, "test-run", []) == 0
    trans.rollback()   # undo, so nothing is actually changed

# The delete removes exactly the rows an ingest of [START, END] would rewrite
with engine.connect() as conn:
    trans = conn.begin()
    probes = [
        (START + LAG + timedelta(seconds=1), f"{gps}_0", 1.0),  # GPS inside its shifted window -> deleted
        (END + LAG + timedelta(seconds=1), f"{gps}_0", 2.0),    # GPS past its shifted window -> kept
        (START + timedelta(seconds=1), soc, 3.0),               # non-GPS inside the window -> deleted
        (END + timedelta(seconds=1), soc, 4.0),                 # non-GPS past the window -> kept
    ]
    insert_cleaned_data(conn, "boundary-test-run", probes)
    _delete_existing_rows(conn, "boundary-test-run", START, END)
    kept = set(conn.execute(
        select(cleaned_data_table.c.value)
        .where(cleaned_data_table.c.runId == "boundary-test-run")
    ).scalars())
    print("kept after delete:", kept)
    assert kept == {2.0, 4.0}, kept
    trans.rollback()


# --- 5. Full ingest ---
# WARNING: ingest_run COMMITS its own transaction, so this really writes to
# whatever NEON_DB_URL points at. Use a dev database or a Neon branch.
def rows_in_window() -> int:
    """Count the rows an ingest of [START, END] writes: non-GPS rows in the
    window, GPS rows in the window shifted by the lag (same ranges as the delete)."""
    c = cleaned_data_table.c
    is_gps = or_(*[c.sensor.startswith(n, autoescape=True) for n in GPS_NAMES])
    with engine.connect() as conn:
        return conn.execute(
            select(func.count()).select_from(cleaned_data_table).where(
                c.runId == RUN_ID,
                or_(
                    and_(~is_gps, c.time.between(START, END)),
                    and_(is_gps, c.time.between(START + LAG, END + LAG)),
                ),
            )
        ).scalar()


df = ingest_run(engine, penelope, RUN_ID, START, END)
print(df.head(10).to_string())

# Exactly the columns the estimation service expects
assert list(df.columns) == ["time", "sensor", "value"], df.columns

# Everything returned was written
first_count = rows_in_window()
print("rows returned:", len(df), "| rows in table:", first_count)
assert first_count == len(df)

# No raw Penelope tags in the output or the table
with engine.connect() as conn:
    table_sensors = set(conn.execute(
        select(cleaned_data_table.c.sensor).distinct()
        .where(cleaned_data_table.c.runId == RUN_ID)
    ).scalars())
raw_tags = set(TAG_TO_NAME)
assert not raw_tags & set(df["sensor"]), raw_tags & set(df["sensor"])
assert not raw_tags & table_sensors, raw_tags & table_sensors

# SoC is on 0-100
soc_values = df.loc[df["sensor"] == soc, "value"]
print("SoC min/max:", soc_values.min(), soc_values.max())
assert soc_values.empty or (soc_values.min() >= 0 and 1 < soc_values.max() <= 100)

# Every sensor in cleaned_data, including suffixed ones, exists in `sensors`
with engine.connect() as conn:
    known = set(conn.execute(select(sensors_table.c.name)).scalars())
assert table_sensors <= known, table_sensors - known
print("sensors:", sorted(table_sensors))

# Every catalog raw tag is mapped to its clean name in `sensor_sources`
with engine.connect() as conn:
    sources = dict(conn.execute(
        select(sensor_sources_table.c.sourceDataTypeName, sensor_sources_table.c.sensor)
    ).all())
assert all(sources.get(tag) == name for tag, name in TAG_TO_NAME.items())

# NEEDS INVESTIGATION sensors are ingested (only ones present in this window show up)
present = {n for n in INVESTIGATION_NAMES if df["sensor"].str.startswith(n).any()}
print("investigation sensors in output:", sorted(present))

# Rerun replaces instead of duplicating
ingest_run(engine, penelope, RUN_ID, START, END)
print("rows after rerun:", rows_in_window())
assert rows_in_window() == first_count


# --- 6. A run with no matching data fails clearly ---
try:
    ingest_run(engine, penelope, "no-such-run", START, END)
    raise AssertionError("expected a ValueError for an empty run")
except ValueError as exc:
    print("empty run raised as expected:", exc)

print("all checks passed")