from repositories.race_repository import RaceRepository


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

    def get_races(self, race_date=None):
        # Ask the repository for races.
        return self.repository.get_races(race_date)

    def get_laps(self, race_id: int):
        # Ask the repository for all laps in a race.
        return self.repository.get_laps(race_id)

    def get_lap(self, race_id: int, lap_number: int):
        # Ask the repository for one specific lap.
        return self.repository.get_lap(race_id, lap_number)

    def get_positions(
        self,
        race_id: int,
        lap_number: int,
        min_lat=None,
        max_lat=None,
        min_lon=None,
        max_lon=None
    ):
        # Ask the repository for position data.
        return self.repository.get_positions(
            race_id,
            lap_number,
            min_lat,
            max_lat,
            min_lon,
            max_lon
        )

    def get_energy(self, race_id, lap_number):
        return self.repository.get_lap_energy(race_id, lap_number)
    
    def get_average_speed(self, race_id: int, lap_number: int):
        # Ask the repository for average speed.
        return self.repository.get_average_speed(
            race_id,
            lap_number
        )

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

    def get_average_speed_between(
        self,
        race_id: int,
        lap_number: int,
        start_latitude: float,
        start_longitude: float,
        end_latitude: float,
        end_longitude: float
    ):
        # Ask the repository for average speed between two positions.
        return self.repository.get_average_speed_between(
            race_id,
            lap_number,
            start_latitude,
            start_longitude,
            end_latitude,
            end_longitude
        )

    def get_race(self, race_id):
        return self.repository.get_race(race_id)