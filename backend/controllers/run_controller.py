from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.engine import Connection

from orion.connection import get_connection
from services.LapNotFoundError import LapNotFoundError
from services.run_service import RunService
from services.RunNotFoundError import RunNotFoundError

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
@router.get("")
def get_runs(conn: DbConnection):
    return service.get_runs(conn)

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

# Get position data for a whole run (wired to OrionDB)
@router.get("/{run_id}/positions")
def get_run_positions(
    conn: DbConnection,
    run_id: UUID):
    try:
        return service.get_run_positions(
            conn,
            run_id,
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

# Get position data for a lap (wired to OrionDB)
@router.get("/{run_id}/laps/{lap_number}/positions")
def get_lap_positions(
    conn: DbConnection,
    run_id: UUID,
    lap_number: LapNumber):
    try:
        return service.get_lap_positions(
            conn,
            run_id,
            lap_number
        )
    # an unknown run and a lap with no data are both a 404
    except (RunNotFoundError, LapNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

"""
General lap information
"""