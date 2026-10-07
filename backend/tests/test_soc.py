from dotenv import load_dotenv; load_dotenv()
import logging
from datetime import UTC, datetime

from penelope.client import PenelopeClient

from orion.ingest import _normalize_soc, _soc_scale

logging.basicConfig(level=logging.INFO)

scale = _soc_scale(
    PenelopeClient.from_env(),
    "5eee6c81-e84d-4f08-b8c4-bc1a481a5ad6",
    datetime(2026, 8, 15, 18, 17, tzinfo=UTC),
    datetime(2026, 8, 15, 18, 19, tzinfo=UTC),
)
print("scale:", scale)
print("0.85 ->", _normalize_soc([0.85], scale))
  