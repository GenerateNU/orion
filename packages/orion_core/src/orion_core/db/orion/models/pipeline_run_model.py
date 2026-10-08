from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.db.orion.base import Base


class PipelineStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PipelineRun(Base):
    """A pipeline job for one run. This table IS the job queue: the worker
    claims the oldest `queued` row (see orion_pipeline/jobs/job_queue.py)."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"))
    status: Mapped[str] = mapped_column(String, default=PipelineStatus.QUEUED)
    error: Mapped[str | None] = mapped_column(String)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
