from uuid import UUID


class LapNotFoundError(Exception):
    """The run exists, but has no data for this lap."""

    def __init__(self, run_id: UUID, lap_number: int):
        super().__init__(f"Lap {lap_number} not found for run {run_id}")
        self.run_id = run_id
        self.lap_number = lap_number

