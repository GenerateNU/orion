class RunNotFoundError(Exception):
    """No run with this ID exists."""

    def __init__(self, run_id: str):
        super().__init__(f"Run {run_id} not found")
        self.run_id = run_id