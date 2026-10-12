import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.engine import Connection

from orion.connection import get_connection
from services.exceptions import RunNotFoundError
from services.run_service import RunService

#this file creates all the API endpoints

# Create a group of run-related API endpoints
router = APIRouter(prefix="/api/runs")

# Create our service
service = RunService()

"""
General Run Information that user might pull
"""

# Shorthand for "give this endpoint a database connection" (see orion/connection.py)
DbConnection = Annotated[Connection, Depends(get_connection)]

# Run IDs are UUIDs, so a malformed one is a 422. Lap numbers start at 1, so 0 or
# negative is a 422 before any query runs
LapNumber = Annotated[int, Path(ge=1)]

# Get runs (wired to OrionDB)
# date is parsed as a real date so a malformed one is a 422, not a DB error
@router.get("")
def get_runs(conn: DbConnection, date: datetime.date | None = None):
    return service.get_runs(conn, date)

# STUB: Get information for a specific run (instead of all runs + includes all laps)
@router.get("/{run_id}")
def get_specific_run(run_id: UUID):
    return service.get_specific_run(run_id)


# STUB: Get all laps for a run
@router.get("/{run_id}/laps")
def get_laps(run_id: UUID):
    return service.get_laps(run_id)

# STUB: Get one specific lap
@router.get("/{run_id}/laps/{lap_number}")
def get_specific_lap(run_id: UUID, lap_number: int):
    return service.get_specific_lap(run_id, lap_number)

"""
Specific information about positions (Maybe we just combine into summary)
"""

# Get position data for a lap (wired to OrionDB)
@router.get("/{run_id}/laps/{lap_number}/positions")
def get_positions(
    conn: DbConnection,
    run_id: UUID,
    lap_number: LapNumber,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
):
    try:
        return service.get_positions(
            conn,
            run_id,
            lap_number,
            min_lat,
            max_lat,
            min_lon,
            max_lon,
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

# STUB: Get energy for a lap
@router.get("/{run_id}/laps/{lap_number}/energy")
def get_lap_energy(
     run_id: UUID,
     lap_number: int,
): 
    return service.get_lap_energy(
        run_id,
        lap_number, 

    )

# STUB: Get velocity at a specific position
# {position} is part of the URL but the lookup only uses latitude/longitude, so
# it isn't passed on (passing it used to crash the endpoint with a 500).
@router.get("/{run_id}/laps/{lap_number}/{position}")
def get_velocity_at_position(
    run_id: UUID,
    lap_number: int,
    position: int,
    latitude: float,
    longitude: float,
):
    return service.get_velocity_at_position(
        run_id,
        lap_number,
        latitude,
        longitude,
    )

"""
General lap information
"""