from dataclasses import dataclass


@dataclass
class RunContext:
    """What a step knows about the job it's running in.

    Steps take this instead of a bare run_id, so later we can add fields
    (time range, config, progress reporting) without changing every step.
    """

    run_id: str
