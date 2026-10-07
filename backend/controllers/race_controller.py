import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.engine import Connection

from orion.connection import get_connection
from services.race_service import RaceService
from services.exceptions import RaceNotFoundError

#this file creates all the API endpoints

# Create a group of race-related API endpoints
router = APIRouter(prefix="/api/races")

# Create our service
service = RaceService()

"""
General Race Information that user might pull
"""

# Shorthand for "give this endpoint a database connection" (see orion/db.py)
DbConnection = Annotated[Connection, Depends(get_connection)]

# IDs and lap numbers start at 1, so 0 or negative is a 422 before any query runs
RaceId = Annotated[int, Path(ge=1)]
LapNumber = Annotated[int, Path(ge=1)]

# Get races (wired to OrionDB)
# date is parsed as a real date so a malformed one is a 422, not a DB error
@router.get("")
def get_races(conn: DbConnection, date: datetime.date | None = None):
    return service.get_races(conn, date)

# STUB: Get information for a specific race (instead of all races + includes all laps)
@router.get("/{race_id}")
def get_specific_race(race_id: int):
    return service.get_specific_race(race_id)


# STUB: Get all laps for a race
@router.get("/{race_id}/laps")
def get_laps(race_id: int):
    return service.get_laps(race_id)

# STUB: Get one specific lap
@router.get("/{race_id}/laps/{lap_number}")
def get_specific_lap(race_id: int, lap_number: int):
    return service.get_specific_lap(race_id, lap_number)

"""
Specific information about positions (Maybe we just combine into summary)
"""

# Get position data for a lap (wired to OrionDB)
@router.get("/{race_id}/laps/{lap_number}/positions")
def get_positions(
    conn: DbConnection,
    race_id: RaceId,
    lap_number: LapNumber,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
):
    try:
        return service.get_positions(
            conn,
            race_id,
            lap_number,
            min_lat,
            max_lat,
            min_lon,
            max_lon,
        )
    except RaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

# STUB: Get energy for a lap
@router.get("/{race_id}/laps/{lap_number}/energy")
def get_lap_energy(
     race_id: int,
     lap_number: int,
): 
    return service.get_lap_energy(
        race_id,
        lap_number, 

    )

# STUB: Get velocity at a specific position
# {position} is part of the URL but the lookup only uses latitude/longitude, so
# it isn't passed on (passing it used to crash the endpoint with a 500).
@router.get("/{race_id}/laps/{lap_number}/{position}")
def get_velocity_at_position(
    race_id: int,
    lap_number: int,
    position: int,
    latitude: float,
    longitude: float,
):
    return service.get_velocity_at_position(
        race_id,
        lap_number,
        latitude,
        longitude,
    )

"""
General lap information
"""