from collections.abc import Sequence

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from orion_core.models import PipelineRun, PipelineStatus, Run
from orion_core.queries.orion_queries import (
    select_active_pipeline_run,
    select_pipeline_runs,
)


class JobAlreadyActiveError(Exception):
    """The run already has a queued or running job."""

    def __init__(self, job: PipelineRun):
        self.job = job
        super().__init__(
            f"Run '{job.run_id}' already has a {job.status} pipeline job ({job.id})"
        )


class JobQueue:
    """The `pipeline_runs` table used as a job queue (no Redis/Celery needed)."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def enqueue(self, run_id: str) -> PipelineRun:
        """Queue a job for `run_id`. Raises JobAlreadyActiveError if one is already
        queued or running, so the same run is never processed twice at once."""
        with Session(self.engine, expire_on_commit=False) as session, session.begin():
            active = session.scalar(select_active_pipeline_run(run_id))
            if active is not None:
                raise JobAlreadyActiveError(active)
            session.execute(insert(Run).values(run_id=run_id).on_conflict_do_nothing())
            job = PipelineRun(run_id=run_id)
            session.add(job)
        return job

    def get(self, job_id: int) -> PipelineRun | None:
        with Session(self.engine) as session:
            return session.get(PipelineRun, job_id)

    def list(
        self, run_id: str | None = None, status: str | None = None, limit: int = 50
    ) -> Sequence[PipelineRun]:
        """Jobs, newest first, optionally for one run and/or one status."""
        with Session(self.engine) as session:
            return session.scalars(select_pipeline_runs(run_id, status, limit)).all()

    def claim_next(self) -> PipelineRun | None:
        """Take the oldest queued job. SKIP LOCKED means two workers never get the same one."""
        with Session(self.engine, expire_on_commit=False) as session, session.begin():
            job = session.scalar(
                select(PipelineRun)
                .where(PipelineRun.status == PipelineStatus.QUEUED)
                .order_by(PipelineRun.queued_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if job is not None:
                job.status = PipelineStatus.RUNNING
        return job

    def finish(self, job_id: int, error: str | None = None) -> None:
        with Session(self.engine) as session, session.begin():
            job = session.get_one(PipelineRun, job_id)
            job.status = PipelineStatus.FAILED if error else PipelineStatus.SUCCEEDED
            job.error = error
