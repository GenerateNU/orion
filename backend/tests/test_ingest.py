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
