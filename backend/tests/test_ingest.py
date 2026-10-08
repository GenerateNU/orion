from dotenv import load_dotenv; load_dotenv()
import logging
from datetime import UTC, datetime

from orion.ingest import (
    _flag_investigation_tags,
    _normalize_soc,
    _soc_scale,
)
from penelope.client import PenelopeClient

logging.basicConfig(level=logging.INFO)

scale = _soc_scale(
    PenelopeClient.from_env(),
    "5eee6c81-e84d-4f08-b8c4-bc1a481a5ad6",
    datetime(2026, 8, 15, 18, 17, tzinfo=UTC),
    datetime(2026, 8, 15, 18, 19, tzinfo=UTC),
)
print("scale:", scale)
print("0.85 ->", _normalize_soc([0.85], scale))




  # --- NEEDS INVESTIGATION flagging  ---
print("found:", _flag_investigation_tags("test-run", {"bms_temp_avg", "gps_mode", "vcu_tsms"}))
print("found:", _flag_investigation_tags("test-run", {"bms_temp_avg", "vcu_speed"}))

# --- clean chunk: rename, SoC, split ---
chunk = [
    ("t1", "VCU_Ethernet/A/Acceleration", "run", [-870.0, -24.6, 486.0]),
    ("t2", "BMS/Pack/SoC", "run", [0.637]),
]

from orion.ingest import _clean_chunk

t = datetime(2026, 8, 15, 18, 17, 3, tzinfo=UTC)
chunk = [
    (t, "VCU_Ethernet/A/Acceleration", "run", [-870.0, -24.6, 486.0]),
    (t, "BMS/Pack/SoC", "run", [0.637]),
    (t, "VCU/CarState/speed", "run", [42.0]),
    (t, "TPU/GPS/Location", "run", [42.33, -71.09]),
]
for row in _clean_chunk(chunk, 100.0):
    print(row)


import os
from sqlalchemy import create_engine
from orion.ingest import _delete_existing_rows

engine = create_engine(os.environ["NEON_DB_URL"])
with engine.connect() as conn:
    trans = conn.begin()
    n = _delete_existing_rows(
        conn,
        "5eee6c81-e84d-4f08-b8c4-bc1a481a5ad6",
        datetime(2026, 8, 15, 18, 17, tzinfo=UTC),
        datetime(2026, 8, 15, 18, 19, tzinfo=UTC),
    )
    print("would delete:", n)
    trans.rollback()   # undo, so nothing is actually deleted


from sqlalchemy import func, select
from orion.ingest import insert_cleaned_data
from orion.schema import cleaned_data_table

fake_rows = [
    (datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC), "bms_pack_soc", 63.7),
    (datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC), "vcu_speed", 42.0),
]
with engine.connect() as conn:
    trans = conn.begin()
    n = insert_cleaned_data(conn, "test-run", fake_rows)
    count = conn.execute(
        select(func.count()).select_from(cleaned_data_table)
        .where(cleaned_data_table.c.runId == "test-run")
    ).scalar()
    print("inserted:", n, "| in table:", count)
    print("empty chunk:", insert_cleaned_data(conn, "test-run", []))
    trans.rollback()  