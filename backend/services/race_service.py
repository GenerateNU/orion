from repositories.race_repository import RaceRepository
from services.exceptions import RaceNotFoundError

class RaceService:

    '''
        intermediate layer between controller and repository.
        this is where you can add logic, validation,
        or any other processing before sending the data to the controller. 

        If we end up doing math in between our data and what needs to get pulled 
        (if we put in two specific positions get the data between that)
    '''

    def __init__(self):
        # Create the repository that this service will use.
        self.repository = RaceRepository()

    def get_races(self, conn, race_date=None):
        # Ask the repository for races.
        return self.repository.get_races(conn, race_date)

    # STUB: returns sample data until a laps table exists in OrionDB.
    def get_laps(self, race_id: int):
        # Ask the repository for all laps in a race.
        return self.repository.get_laps(race_id)

    # STUB: returns sample data until a laps table exists in OrionDB.
    def get_specific_lap(self, race_id: int, lap_number: int):
        # Ask the repository for one specific lap.
        return self.repository.get_specific_lap(race_id, lap_number)


    def get_positions(
        self,
        conn,
        race_id: int,
        lap_number: int,
        min_lat=None,
        max_lat=None,
        min_lon=None,
        max_lon=None
    ):
        # A race with no positions yet returns [], but a race that doesn't
        # exist at all is an error -- otherwise a typo'd ID looks like "no data".
        if not self.repository.race_exists(conn, race_id):
            raise RaceNotFoundError(race_id)

        # Ask the repository for position data.
        return self.repository.get_positions(
            conn,
            race_id,
            lap_number,
            min_lat,
            max_lat,
            min_lon,
            max_lon
        )

    # STUB: returns sample data until energy is computed into OrionDB.
    def get_lap_energy(self, race_id, lap_number):
        return self.repository.get_lap_energy(race_id, lap_number)


    # STUB: returns sample data until velocity is computed into OrionDB.
    def get_velocity_at_position(
        self,
        race_id: int,
        lap_number: int,
        latitude: float,
        longitude: float
    ):
        # Ask the repository for velocity at a specific position.
        return self.repository.get_velocity_at_position(
            race_id,
            lap_number,
            latitude,
            longitude
        )

    # STUB: returns sample data -- not wired to the races table yet.
    def get_specific_race(self, race_id):
        return self.repository.get_specific_race(race_id)