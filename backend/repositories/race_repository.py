from sqlalchemy import exists, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from orion.exceptions import OrionConnectionError, OrionSchemaError
from orion.schema import estimated_positions_table, races_table


def _run(conn: Connection, stmt):
    """Execute a query, raising Orion errors instead of SQLAlchemy ones."""
    try:
        return conn.execute(stmt)
    except OperationalError as exc:
        raise OrionConnectionError("Lost connection to OrionDB mid-query.") from exc
    except SQLAlchemyError as exc:
        # Connected but the query failed -- usually the table doesn't exist yet.
        # Must come second: OperationalError is a SQLAlchemyError subclass.
        raise OrionSchemaError(
            "Query against OrionDB failed. If the races/estimated_positions "
            "tables are missing, run setup_orion.py."
        ) from exc


class RaceRepository:

    # Get all races (wired to OrionDB)
    def get_races(self, conn: Connection, date=None):
        stmt = select(races_table).order_by(races_table.c.race_id)
        if date is not None:
            stmt = stmt.where(races_table.c.dates == date)
        return [dict(row._mapping) for row in _run(conn, stmt)]

    # Check a race exists, so the API can 404 instead of returning [] for a typo
    def race_exists(self, conn: Connection, race_id):
        stmt = select(exists().where(races_table.c.race_id == race_id))
        return bool(_run(conn, stmt).scalar())

    # Get all laps for a race
    def get_laps(self, race_id):
        return [
            {
                "race_id": race_id,
                "lap_number": 1,
                "time_seconds": 92.5,
                "average_speed": 45.2,
                "energy_consumption": 2.4,
                "energy_regenerated": 0.5,
                "efficiency": 0.82,
            }
        ]

    # Get one lap
    def get_specific_lap(self, race_id, lap_number):
        return {
            "race_id": race_id,
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
        race_id,
        lap_number,
        min_lat=None,
        max_lat=None,
        min_lon=None,
        max_lon=None,
    ):
        t = estimated_positions_table
        stmt = (
            select(t.c.timestamp, t.c.latitude, t.c.longitude)
            .where(t.c.race_id == race_id, t.c.lap_number == lap_number)
            .order_by(t.c.timestamp)
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


    # Get velocity at a position
    def get_velocity_at_position(
        self,
        race_id,
        lap_number,
        latitude,
        longitude,
    ):
        return {
            "latitude": latitude,
            "longitude": longitude,
            "speed": 40.0,
        }
    
    # Get a specific race as well 

    def get_specific_race(self, race_id):
        return {
            "race_id": race_id, 
            "name": "Sample Race",
            "date": "2026-09-10"
        }
    
    #energy consumption per lap 
    def get_lap_energy(self, race_id, lap_number):
        return {
            "race_id": race_id,
            "lap_number": lap_number,
            "energy_consumption": 1.82,
            "energy_regenerated": 0.34,
            "net_energy": 1.48
        }