"""Laps for a run: the pipeline's lap step output in OrionDB `metrics`."""

from datetime import datetime

from pydantic import BaseModel, Field


class LapResponse(BaseModel):
    """One lap of a run."""

    lap_number: int = Field(description="Lap number within the run.", examples=[1])
    start_time: datetime = Field(
        description="Lap start (UTC).", examples=["2026-10-01T14:02:11.000Z"]
    )
    end_time: datetime = Field(description="Lap end (UTC).", examples=["2026-10-01T14:03:42.500Z"])


class MetricsResponse(BaseModel):
    """Every lap for one run, ordered by lap number."""

    run_id: str = Field(description="Penelope run id.", examples=["run-123"])
    laps: list[LapResponse] = Field(
        default_factory=list, description="Laps in order. Empty if the run has none."
    )
