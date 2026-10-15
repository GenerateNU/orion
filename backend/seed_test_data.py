"""Put a few fake runs into OrionDB so the API and frontend have something to show.

    uv run python seed_test_data.py            # add the test runs (safe to re-run)
    uv run python seed_test_data.py --delete   # remove them again

Every test run has a fixed UUID starting with 7e57 ("test") and a name starting
with "TEST", so they're easy to spot and --delete only ever touches those rows.
(The frontend labels runs by their first 8 characters, so those differ per run.)
Each run gets 3 laps of a made-up loop around Boston, ~0.43 s between points,
like the frontend's mock data.
"""

from dotenv import load_dotenv

load_dotenv()

import math
import sys
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import bindparam, delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from orion.connection import get_engine
from orion.exceptions import OrionConfigError
from orion.schema import estimated_car_state_table

LAPS = 3
POINTS_PER_LAP = 220
SECONDS_BETWEEN_POINTS = 0.43

# (run id, name, race date, track wobble -- see lap_rows)
TEST_RUNS = [
    (UUID("7e57a001-0000-4000-8000-000000000000"), "TEST seed run A", date(2026, 10, 4), (0.0007, 3, 0.0009, 2)),
    (UUID("7e57b002-0000-4000-8000-000000000000"), "TEST seed run B", date(2026, 9, 27), (0.0011, 2, 0.0004, 4)),
]
TEST_RUN_IDS = [run_id for run_id, *_ in TEST_RUNS]


def lap_rows(run_id, race_date, shape):
    """Every estimated_car_state row for one run: LAPS laps of a wobbly loop."""
    a, n, b, m = shape
    start = datetime(race_date.year, race_date.month, race_date.day, 14, tzinfo=UTC)
    rows = []
    for lap in range(1, LAPS + 1):
        for i in range(POINTS_PER_LAP):
            t = i / POINTS_PER_LAP * 2 * math.pi
            # a little lap-to-lap variation so laps don't look identical
            drift = 0.00008 * (lap - 1) * math.sin(5 * t)
            seconds = ((lap - 1) * POINTS_PER_LAP + i) * SECONDS_BETWEEN_POINTS
            rows.append({
                "runId": run_id,
                "time": start + timedelta(seconds=seconds),
                "lapId": lap,
                "latitude": 42.3398 + 0.0022 * math.sin(t) + a * math.sin(n * t) + drift,
                "longitude": -71.0892 + 0.0045 * math.cos(t) + b * math.cos(m * t + 0.6),
            })
    return rows


# pipeline_runs isn't in orion/schema.py (it's internal), and its `stage` column
# is a Postgres enum, so it's written with plain SQL.
INSERT_RUN = text(
    'INSERT INTO pipeline_runs ("runId", name, "raceDate", stage) '
    "VALUES (:run_id, :name, :race_date, CAST(:stage AS pipeline_stage)) "
    'ON CONFLICT ("runId") DO NOTHING'
)
DELETE_RUNS = text('DELETE FROM pipeline_runs WHERE "runId" IN :ids').bindparams(
    bindparam("ids", expanding=True)
)


def seed(conn):
    for run_id, name, race_date, shape in TEST_RUNS:
        conn.execute(INSERT_RUN, {
            "run_id": run_id, "name": name, "race_date": race_date, "stage": "laps_detected",
        })
        # (runId, time) is the primary key, so re-running skips rows already there
        stmt = pg_insert(estimated_car_state_table).on_conflict_do_nothing()
        conn.execute(stmt, lap_rows(run_id, race_date, shape))
        print(f"seeded {name} ({run_id}): {LAPS} laps x {POINTS_PER_LAP} points")


def unseed(conn):
    t = estimated_car_state_table
    # car states first: they reference pipeline_runs
    states = conn.execute(delete(t).where(t.c.runId.in_(TEST_RUN_IDS))).rowcount
    runs = conn.execute(DELETE_RUNS, {"ids": [str(i) for i in TEST_RUN_IDS]}).rowcount
    print(f"deleted {states} car states and {runs} runs")


if __name__ == "__main__":
    try:
        engine = get_engine()
    except OrionConfigError as exc:
        raise SystemExit(str(exc)) from exc

    # one transaction: either everything is written (or deleted), or nothing is
    with engine.begin() as conn:
        if "--delete" in sys.argv:
            unseed(conn)
        else:
            seed(conn)
