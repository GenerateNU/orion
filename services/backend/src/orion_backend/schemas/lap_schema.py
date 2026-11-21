"""Laps: the pipeline's lap step output in OrionDB `laps`."""

from datetime import datetime

from pydantic import BaseModel, Field


class LapResponse(BaseModel):
    """One lap: from one start/finish line crossing to the next."""

    lap_id: int = Field(description="Lap number within the run, from 1.", examples=[3])
    start_time: datetime = Field(description="When the lap starts (UTC).")
    end_time: datetime = Field(description="When the lap ends (UTC).")


class LapsResponse(BaseModel):
    """Every lap of one run, in order."""

    run_id: str = Field(description="Penelope run id.", examples=["run-123"])
    laps: list[LapResponse] = Field(default_factory=list)
