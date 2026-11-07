"""How far through its lap the car is, from OrionDB `laps` and `estimated_car_state`."""

from datetime import datetime

from pydantic import BaseModel, Field


class LapProgressResponse(BaseModel):
    """Lap progress for one run between `start` and `end`: `progress[i]` is how far
    through its lap the car is at `time[i]` (see docs/lap_progress.md)."""

    run_id: str = Field(description="Penelope run id.", examples=["run-123"])
    start: datetime = Field(description="Inclusive lower time bound, as requested.")
    end: datetime = Field(description="Inclusive upper time bound, as requested.")
    time: list[datetime] = Field(
        default_factory=list,
        description="Row timestamps (UTC), ascending.",
        examples=[["2026-10-01T14:02:11.000Z", "2026-10-01T14:02:11.010Z"]],
    )
    progress: list[float] = Field(
        default_factory=list,
        description="From 0 to 1, same length as `time`.",
        examples=[[0.412, 0.413]],
    )
    lap_id: list[int] = Field(
        default_factory=list,
        description="The lap each point is in, same length as `time`.",
        examples=[[3, 3]],
    )
