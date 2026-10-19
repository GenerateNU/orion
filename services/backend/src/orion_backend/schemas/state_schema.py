"""Estimated car state: the pipeline's 100 Hz output in OrionDB `estimated_car_state`."""

from datetime import datetime

from pydantic import BaseModel, Field


class StateDataResponse(BaseModel):
    """Estimated car positions for one run between `start` and `end`:
    `positions[i]` is the `[lat, lon]` estimate at `time[i]`."""

    run_id: str = Field(description="Penelope run id.", examples=["run-123"])
    start: datetime = Field(description="Inclusive lower time bound, as requested.")
    end: datetime = Field(description="Inclusive upper time bound, as requested.")
    time: list[datetime] = Field(
        default_factory=list,
        description="Row timestamps (UTC), ascending.",
        examples=[["2026-10-01T14:02:11.000Z", "2026-10-01T14:02:11.010Z"]],
    )
    positions: list[tuple[float, float]] = Field(
        default_factory=list,
        description=(
            "`[latitude, longitude]` in degrees, same length as `time`. Lat-first, so it "
            "can be passed straight to Leaflet."
        ),
        examples=[[[42.3398, -71.0892], [42.3399, -71.0890]]],
    )
