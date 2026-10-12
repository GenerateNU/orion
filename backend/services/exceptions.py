from uuid import UUID


class RunNotFoundError(Exception):
    """No run with this ID exists."""

    def __init__(self, run_id: UUID):
        super().__init__(f"Run {run_id} not found")
        self.run_id = run_id


class LapNotFoundError(Exception):
    """The run exists, but has no data for this lap."""

    def __init__(self, run_id: UUID, lap_number: int):
        super().__init__(f"Lap {lap_number} not found for run {run_id}")
        self.run_id = run_id
        self.lap_number = lap_number
