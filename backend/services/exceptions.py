class RaceNotFoundError(Exception):
    """No race with this ID exists."""

    def __init__(self, race_id: int):
        super().__init__(f"Race {race_id} not found")
        self.race_id = race_id