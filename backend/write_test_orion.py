from dotenv import load_dotenv

load_dotenv()

from datetime import UTC, datetime

import numpy as np

from orion.db import get_engine
from orion.exceptions import OrionConfigError
from orion.repository import DataPointRepository
from penelope.client import PenelopeClient

# get_engine checks NEON_DB_URL and pins the psycopg2 driver (see setup_orion.py)
try:
    engine = get_engine()
except OrionConfigError as exc:
    raise SystemExit(str(exc)) from exc

penelope = PenelopeClient.from_env()
repo = DataPointRepository(engine)

points = penelope.get_by_time_bounds(
    datetime(2026, 8, 15, 22, 45, tzinfo=UTC),
    datetime(2026, 8, 15, 22, 55, tzinfo=UTC),
)
print(f"pulled {len(points)} points from Penelope")

# Re-running this over a window already stored inserts 0 and raises nothing --
# the primary key plus ON CONFLICT DO NOTHING makes ingest idempotent.
inserted = repo.write_many(points)
print(f"wrote {inserted} new points to Orion ({len(points) - inserted} already present)")

# An empty batch should short-circuit without touching the database.
empty = np.empty((0, 4), dtype=object)
assert repo.write_many(empty) == 0
print("empty array correctly wrote 0 points")
