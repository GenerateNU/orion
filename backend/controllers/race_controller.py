import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Connection

from orion.db import get_connection
from services.race_service import RaceNotFoundError, RaceService

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

# Get races (wired to OrionDB)
# date is parsed as a real date so a malformed one is a 422, not a DB error
@router.get("")
def get_races(conn: DbConnection, date: datetime.date | None = None):
    return service.get_races(conn, date)

# Get information for a specific race (instead of all races + includes all laps)
@router.get("/{race_id}")
def get_specific_race(race_id: int): 
    return service.get_specific_race(race_id)


# Get all laps for a race 
@router.get("/{race_id}/laps")
def get_laps(race_id: int):
    return service.get_laps(race_id)

# Get one specific lap 
@router.get("/{race_id}/laps/{lap_number}")
def get_specific_lap(race_id: int, lap_number: int):
    return service.get_lap(race_id, lap_number)

"""
Specific information about positions (Maybe we just combine into summary)
"""

# Get position data for a lap (wired to OrionDB)
@router.get("/{race_id}/laps/{lap_number}/positions")
def get_positions(
    conn: DbConnection,
    race_id: int,
    lap_number: int,
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

# Get energy for a lap
@router.get("/{race_id}/laps/{lap_number}/energy")
def get_lap_energy(
     race_id: int,
     lap_number: int,
): 
    return service.get_lap_energy(
        race_id,
        lap_number, 

    )

# Get velocity at a specific position
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
        position,
        latitude,
        longitude,
    )

"""
General lap information
"""