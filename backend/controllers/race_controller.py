from fastapi import APIRouter

from services.race_service import RaceService

#this file creates all the API endpoints

# Create a group of race-related API endpoints
router = APIRouter(prefix="/api/races")

# Create our service
service = RaceService()

"""
General Race Information that user might pull
"""

# Get races 
@router.get("")
def get_races(date: str | None = None):
    return service.get_races(date)

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

# Get position data for a lap 
@router.get("/{race_id}/laps/{lap_number}/positions")
def get_positions(
    race_id: int,
    lap_number: int,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
):
    return service.get_positions(
        race_id,
        lap_number,
        min_lat,
        max_lat,
        min_lon,
        max_lon,
    )

# Get energy for a lap
@router.get("/{race_id}/laps/{lap_number}/energy")
def get_energy(
     race_id: int,
     lap_number: int,
): 
    return service.get_energy(
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
Endpoints for in between 2 positions 
"""
# Get average speed between two positions
@router.get("/{race_id}/laps/{lap_number}/{position}")
def get_average_speed_between(
    race_id: int,
    lap_number: int,
    position: int,
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
):
    return service.get_average_speed_between(
        race_id,
        lap_number,
        position,
        start_latitude,
        start_longitude,
        end_latitude,
        end_longitude,
    )
