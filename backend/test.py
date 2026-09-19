"""
Quick manual test for PenelopeClient. Requires VPN connected and a `.env`
file with the PENELOPE_DB_* variables set.
"""

from datetime import datetime, timezone

from dotenv import load_dotenv
from penelope.client import PenelopeClient

load_dotenv()

client = PenelopeClient.from_env()

start = datetime(2026, 8, 15, 21, 55, tzinfo=timezone.utc)
end = datetime(2026, 8, 15, 22, 55, tzinfo=timezone.utc)
run_id = "e6745f54-8687-41e7-aabb-c88c0d04243c"

time_points = client.get_by_time_bounds(start, end)
print(f"get_by_time_bounds: {len(time_points)} points")
print(time_points[0])

run_points = client.get_by_run_id(run_id)
print(f"get_by_run_id: {len(run_points)} points")
print(run_points[0])