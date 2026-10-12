from sqlalchemy import exists, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from orion.exceptions import OrionConnectionError, OrionSchemaError
from orion.schema import estimated_car_state_table


def _run(conn: Connection, stmt):
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

    # Get all runs, newest first (wired to OrionDB)
    # A run is any runId in estimated_car_state; there's no runs table, so a run
    # has no name, and its date is the (UTC) day of its first estimate.
    def get_runs(self, conn: Connection, date=None):
        t = estimated_car_state_table
        stmt = (
            select(t.c.runId, func.min(t.c.time).label("started"))
            .group_by(t.c.runId)
            .order_by(func.min(t.c.time).desc())
        )
        runs = [
            {"run_id": row.runId, "dates": row.started.date()}
            for row in _run(conn, stmt)
        ]
        # filtered here rather than in SQL: Postgres and SQLite turn a
        # timestamp into a date differently, and there are only a handful of runs
        if date is not None:
            runs = [run for run in runs if run["dates"] == date]
        return runs

    # Check a run exists, so the API can 404 instead of returning [] for a typo
    def run_exists(self, conn: Connection, run_id):
        stmt = select(exists().where(estimated_car_state_table.c.runId == run_id))
        return bool(_run(conn, stmt).scalar())

    # ---- STUBS: everything below except get_positions returns sample data. ----
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

    # Get position data for one lap, in time order (wired to OrionDB)
    def get_positions(
        self,
        conn: Connection,
        run_id,
        lap_number,
        min_lat=None,
        max_lat=None,
        min_lon=None,
        max_lon=None,
    ):
        t = estimated_car_state_table
        stmt = (
            select(t.c.time.label("timestamp"), t.c.latitude, t.c.longitude)
            .where(t.c.runId == run_id, t.c.lapId == lap_number)
            .order_by(t.c.time)
        )
        # optional bounding box, each edge independent
        if min_lat is not None:
            stmt = stmt.where(t.c.latitude >= min_lat)
        if max_lat is not None:
            stmt = stmt.where(t.c.latitude <= max_lat)
        if min_lon is not None:
            stmt = stmt.where(t.c.longitude >= min_lon)
        if max_lon is not None:
            stmt = stmt.where(t.c.longitude <= max_lon)
        return [dict(row._mapping) for row in _run(conn, stmt)]


    # STUB: Get velocity at a position
    def get_velocity_at_position(
        self,
        run_id,
        lap_number,
        latitude,
        longitude,
    ):
        return {
            "latitude": latitude,
            "longitude": longitude,
            "speed": 40.0,
        }
    
    # STUB: Get a specific run as well (not yet reading the runs table)
    def get_specific_run(self, run_id):
        return {
            "run_id": run_id, 
            "name": "Sample Run",
            "date": "2026-09-10"
        }
    
    # STUB: energy consumption per lap
    def get_lap_energy(self, run_id, lap_number):
        return {
            "run_id": run_id,
            "lap_number": lap_number,
            "energy_consumption": 1.82,
            "energy_regenerated": 0.34,
            "net_energy": 1.48
        }