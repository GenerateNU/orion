from uuid import UUID

from repositories.run_repository import RunRepository
from services.LapNotFoundError import LapNotFoundError
from services.RunNotFoundError import RunNotFoundError


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

    def get_runs(self, conn):
        # Ask the repository for runs.
        return self.repository.get_runs(conn)

    # STUB: returns sample data until a laps table exists in OrionDB.
    def get_laps(self, run_id: UUID):
        # Ask the repository for all laps in a run.
        return self.repository.get_laps(run_id)

    # STUB: returns sample data until a laps table exists in OrionDB.
    def get_specific_lap(self, run_id: UUID, lap_number: int):
        # Ask the repository for one specific lap.
        return self.repository.get_specific_lap(run_id, lap_number)


    def get_run_positions(
        self,
        conn,
        run_id: UUID,
    ):
        # A run with no positions yet returns [], but a run that doesn't
        # exist at all is an error -- otherwise a typo'd ID looks like "no data".
        if not self.repository.run_exists(conn, run_id):
            raise RunNotFoundError(run_id)

        # Ask the repository for position data.
        return self.repository.get_run_positions(
            conn,
            run_id
        )
    
    def get_lap_positions(
        self,
        conn,
        run_id: UUID,
        lap_number: int
    ):
        # An unknown run or a lap with no data is an error, so a typo'd ID or
        # lap number doesn't look like "no data".
        if not self.repository.run_exists(conn, run_id):
            raise RunNotFoundError(run_id)
        if not self.repository.lap_exists(conn, run_id, lap_number):
            raise LapNotFoundError(run_id, lap_number)

        # Ask the repository for position data.
        return self.repository.get_lap_positions(
            conn,
            run_id,
            lap_number
        )


    # STUB: returns sample data -- not wired to the runs table yet.
    def get_specific_run(self, run_id):
        return self.repository.get_specific_run(run_id)