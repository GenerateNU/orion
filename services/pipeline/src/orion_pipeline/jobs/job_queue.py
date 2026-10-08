from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from orion_core.db.orion.models import PipelineRun, PipelineStatus, Run


class JobQueue:
    """The `pipeline_runs` table used as a job queue (no Redis/Celery needed)."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def enqueue(self, run_id: str) -> PipelineRun:
        with Session(self.engine, expire_on_commit=False) as session, session.begin():
            session.execute(insert(Run).values(run_id=run_id).on_conflict_do_nothing())
            job = PipelineRun(run_id=run_id)
            session.add(job)
        return job

    def get(self, job_id: int) -> PipelineRun | None:
        with Session(self.engine) as session:
            return session.get(PipelineRun, job_id)

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
