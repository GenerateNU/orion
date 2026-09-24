from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime, timezone

from sqlalchemy import create_engine

from penelope.client import PenelopeClient
from orion.exceptions import OrionValidationError
from orion.repository import DataPointRepository

url = os.environ.get("NEON_DB_URL")
if not url:
    raise SystemExit(
        "NEON_DB_URL is not set. Copy .env.example to .env in the repo root "
        "and paste your Neon connection string into it."
    )

penelope = PenelopeClient.from_env()
repo = DataPointRepository(create_engine(url))

points = penelope.get_by_time_bounds(
    datetime(2026, 8, 15, 22, 45, tzinfo=timezone.utc),
    datetime(2026, 8, 15, 22, 55, tzinfo=timezone.utc),
)
print(f"pulled {len(points)} points from Penelope")

# Re-running this over a window already stored inserts 0 and raises nothing --
# the primary key plus ON CONFLICT DO NOTHING makes ingest idempotent.
inserted = repo.write_many(points)
print(f"wrote {inserted} new points to Orion ({len(points) - inserted} already present)")

try:
    repo.write_many(["not a DataPoint", 42])
except OrionValidationError as exc:
    # The message names the offending index, so a bad record in a batch of
    # thousands is findable.
    print(f"correctly rejected invalid records: {str(exc).splitlines()[0]}")
