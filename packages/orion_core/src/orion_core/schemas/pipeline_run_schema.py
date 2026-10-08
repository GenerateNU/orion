"""Pipeline job schemas, shared by the pipeline API and the backend that calls it."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PipelineRunCreate(BaseModel):
    run_id: str = Field(description="Penelope run to process.", examples=["run-123"])


class PipelineRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Pipeline job id (not the Penelope run_id).")
    run_id: str
    status: str = Field(examples=["queued"])
    error: str | None
    queued_at: datetime
