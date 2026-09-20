from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime, timezone
from sqlalchemy import create_engine

from penelope.client import PenelopeClient
from orion.repository import DataPointRepository

penelope = PenelopeClient.from_env()
orion_engine = create_engine(os.environ["NEON_DB_URL"])
repo = DataPointRepository(orion_engine)

points = penelope.get_by_time_bounds(
    datetime(2026, 8, 15, 22, 45, tzinfo=timezone.utc),
    datetime(2026, 8, 15, 22, 55, tzinfo=timezone.utc),
)
print(f"pulled {len(points)} points from Penelope")

repo.write_many(points)
print(f"wrote {len(points)} points to Orion")

try:
    repo.write_many(["not a DataPoint", 42])
except TypeError as e:
    print(f"correctly rejected: {e}")