from pydantic import BaseModel
from orion_core.settings import get_settings

class RunContext(BaseModel):
    """What a step knows about the job it's running in.

    Steps take this instead of a bare run_id, so later we can add fields
    (time range, config, progress reporting) without changing every step.
    """

    run_id: str
    # Seconds added to gps_location timestamps in the clean step.
    gps_time_offset_s: float = get_settings().gps_time_offset_s
