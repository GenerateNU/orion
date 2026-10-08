from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str = Field(description="Penelope run id.", examples=["run-123"])
    created_at: datetime = Field(description="When OrionDB first saw this run.")
