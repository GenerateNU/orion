"""Runs as recorded in Penelope's `run` table (read-only)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PenelopeRunResponse(BaseModel):
    """One Penelope run, with whether Orion has already processed it."""

    model_config = ConfigDict(from_attributes=True)

    run_id: str = Field(
        description=(
            "Penelope `run.id` (uuid). Send this to `POST /pipeline/runs` and use it "
            "as `{run_id}` in every per-run route."
        ),
        examples=["00d5d5a4-b368-4452-b6c7-278311190931"],
    )
    time: datetime | None = Field(
        description="When Penelope recorded the run (UTC).",
        examples=["2026-07-11T16:42:18Z"],
    )
    processed: bool = Field(
        default=False,
        description=(
            "True if the run has a pipeline job that succeeded with no error. "
            "Processed runs can still be processed again."
        ),
    )
