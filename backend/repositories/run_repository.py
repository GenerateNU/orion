from sqlalchemy import exists, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from orion.exceptions import OrionConnectionError, OrionSchemaError
from orion.schema import estimated_car_state_table


def executeQuery(conn: Connection, stmt):
    """Execute a query, raising Orion errors instead of SQLAlchemy ones."""
    try:
        return conn.execute(stmt)
    except OperationalError as exc:
        raise OrionConnectionError("Lost connection to OrionDB mid-query.") from exc
    except SQLAlchemyError as exc:
        # Connected but the query failed -- usually a table or column is missing.
        # Must come second: OperationalError is a SQLAlchemyError subclass.
        raise OrionSchemaError(
            "Query against OrionDB failed. Check that the estimated_car_state "
            "table exists and matches orion/schema.py."
        ) from exc


class RunRepository:

    # Get all runs, most recently active first (wired to OrionDB)
    # A run is any runId in estimated_car_state. Each one is an object rather
    # than a bare ID so fields can be added later without breaking the frontend.
    def get_runs(self, conn: Connection):
        t = estimated_car_state_table

        stmt = (
            select(t.c.runId)
            .group_by(t.c.runId)
            .order_by(func.max(t.c.time).desc())
        )

        return [{"run_id": row.runId} for row in executeQuery(conn, stmt)]


    # Check a run exists, so the API can 404 instead of returning [] for a typo
    def run_exists(self, conn: Connection, run_id):
        stmt = select(exists().where(estimated_car_state_table.c.runId == run_id))
        return bool(executeQuery(conn, stmt).scalar())

    # Check a run has any data for this lap
    # (conditions go in as separate .where() arguments -- Python's `and` doesn't
    # work on SQL expressions)
    def lap_exists(self, conn: Connection, run_id, lap_number):
        t = estimated_car_state_table
        stmt = select(exists().where(t.c.runId == run_id, t.c.lapId == lap_number))
        return bool(executeQuery(conn, stmt).scalar())

    # ---- STUBS: everything below except the two position queries returns sample data. ----
    # Not wired to OrionDB yet; kept so the endpoints keep responding until their
    # tables exist. Don't delete them.

    # STUB: Get all laps for a run
    def get_laps(self, run_id):
        return [
            {
                "run_id": run_id,
                "lap_number": 1,
                "time_seconds": 92.5,
                "average_speed": 45.2,
                "energy_consumption": 2.4,
                "energy_regenerated": 0.5,
                "efficiency": 0.82,
            }
        ]

    # STUB: Get one lap
    def get_specific_lap(self, run_id, lap_number):
        return {
            "run_id": run_id,
            "lap_number": lap_number,
            "time_seconds": 92.5,
            "average_speed": 45.2,
            "energy_consumption": 2.4,
            "energy_regenerated": 0.5,
            "efficiency": 0.82,
        }

    # Get position data for a run, in time order (wired to OrionDB)
    def get_run_positions(
        self,
        conn: Connection,
        run_id,
    ):
        t = estimated_car_state_table
        stmt = (
            select(t.c.time.label("timestamp"), t.c.latitude, t.c.longitude)
            .where(t.c.runId == run_id)
            .order_by(t.c.time)
        )

        return [dict(row._mapping) for row in executeQuery(conn, stmt)]

    # Get position data for one lap of a run, in time order (wired to OrionDB)
    def get_lap_positions(
        self,
        conn: Connection,
        run_id,
        lap_number
    ):
        t = estimated_car_state_table
        stmt = (
            select(t.c.time.label("timestamp"), t.c.latitude, t.c.longitude)
            .where(t.c.runId == run_id, t.c.lapId == lap_number)
            .order_by(t.c.time)
        )

        return [dict(row._mapping) for row in executeQuery(conn, stmt)]

    # STUB: Get a specific run as well (not yet reading the runs table)
    def get_specific_run(self, run_id):
        return {
            "run_id": run_id,
            "name": "Sample Run",
            "date": "2026-09-10"
        }
