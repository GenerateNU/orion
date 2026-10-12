from uuid import UUID

from backend.controllers.run_controller import LapNumber


class RunNotFoundError(Exception):
    """No run with this ID exists."""

    def __init__(self, run_id: UUID):
        super().__init__(f"Run {run_id} not found")
        self.run_id = run_id

class LapNotFoundError(Exception):

    def __init__(self, lap_number: LapNumber):
        super().__init__(f"Lap {lap_number} not found")
        self.lap_number = lap_number