from repositories.run_repository import RunRepository
from services.exceptions import RunNotFoundError


class RunService:

    '''
        intermediate layer between controller and repository.
        this is where you can add logic, validation,
        or any other processing before sending the data to the controller. 

        If we end up doing math in between our data and what needs to get pulled 
        (if we put in two specific positions get the data between that)
    '''

    def __init__(self):
        # Create the repository that this service will use.
        self.repository = RunRepository()

    def get_runs(self, conn, run_date=None):
        # Ask the repository for runs.
        return self.repository.get_runs(conn, run_date)

    # STUB: returns sample data until a laps table exists in OrionDB.
    def get_laps(self, run_id: str):
        # Ask the repository for all laps in a run.
        return self.repository.get_laps(run_id)

    # STUB: returns sample data until a laps table exists in OrionDB.
    def get_specific_lap(self, run_id: str, lap_number: int):
        # Ask the repository for one specific lap.
        return self.repository.get_specific_lap(run_id, lap_number)


    def get_positions(
        self,
        conn,
        run_id: str,
        lap_number: int,
        min_lat=None,
        max_lat=None,
        min_lon=None,
        max_lon=None
    ):
        # A run with no positions yet returns [], but a run that doesn't
        # exist at all is an error -- otherwise a typo'd ID looks like "no data".
        if not self.repository.run_exists(conn, run_id):
            raise RunNotFoundError(run_id)

        # Ask the repository for position data.
        return self.repository.get_positions(
            conn,
            run_id,
            lap_number,
            min_lat,
            max_lat,
            min_lon,
            max_lon
        )

    # STUB: returns sample data until energy is computed into OrionDB.
    def get_lap_energy(self, run_id, lap_number):
        return self.repository.get_lap_energy(run_id, lap_number)


    # STUB: returns sample data until velocity is computed into OrionDB.
    def get_velocity_at_position(
        self,
        run_id: str,
        lap_number: int,
        latitude: float,
        longitude: float
    ):
        # Ask the repository for velocity at a specific position.
        return self.repository.get_velocity_at_position(
            run_id,
            lap_number,
            latitude,
            longitude
        )

    # STUB: returns sample data -- not wired to the runs table yet.
    def get_specific_run(self, run_id):
        return self.repository.get_specific_run(run_id)