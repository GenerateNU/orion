from typing import Annotated, cast
from fastapi import APIRouter, HTTPException, Query, Request, status
from orion_core.models import PipelineStatus
from orion_core.schemas.pipeline_run_schema import (
    PipelineRunCreate,
    PipelineRunResponse,
)
from orion_pipeline.jobs.job_queue import JobAlreadyActiveError, JobQueue

router = APIRouter(prefix="/runs", tags=["runs"])

# Plain `def` endpoints: FastAPI runs them in a thread, so the sync DB calls
# don't block. This API only queues and reads jobs; the worker does the work.


def _queue(request: Request) -> JobQueue:
    return cast(JobQueue, request.app.state.queue)


@router.post(
    "", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED
)
def create_run(body: PipelineRunCreate, request: Request) -> PipelineRunResponse:
    """Queue a job for the worker. 409 if the run already has an active job."""
    try:
        job = _queue(request).enqueue(body.run_id)
    except JobAlreadyActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PipelineRunResponse.model_validate(job)


@router.get("", response_model=list[PipelineRunResponse])
def list_runs(
    request: Request,
    run_id: str | None = None,
    pipeline_status: Annotated[PipelineStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[PipelineRunResponse]:
    """Job history, newest first."""
    jobs = _queue(request).list(run_id, pipeline_status, limit)
    return [PipelineRunResponse.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=PipelineRunResponse)
def get_run(job_id: int, request: Request) -> PipelineRunResponse:
    job = _queue(request).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Pipeline job {job_id} not found")
    return PipelineRunResponse.model_validate(job)
