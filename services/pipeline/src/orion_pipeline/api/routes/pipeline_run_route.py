from fastapi import APIRouter, HTTPException, Request, status

from orion_core.schemas.pipeline_run_schema import (
    PipelineRunCreate,
    PipelineRunResponse,
)
from orion_pipeline.jobs.job_queue import JobQueue

router = APIRouter(prefix="/runs", tags=["runs"])

# Plain `def` endpoints: FastAPI runs them in a thread, so the sync DB calls
# don't block. This API only queues and reads jobs; the worker does the work.


def _queue(request: Request) -> JobQueue:
    return request.app.state.queue


@router.post(
    "", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED
)
def create_run(body: PipelineRunCreate, request: Request) -> PipelineRunResponse:
    """Queue a job for the worker."""
    return PipelineRunResponse.model_validate(_queue(request).enqueue(body.run_id))


@router.get("/{job_id}", response_model=PipelineRunResponse)
def get_run(job_id: int, request: Request) -> PipelineRunResponse:
    job = _queue(request).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Pipeline job {job_id} not found")
    return PipelineRunResponse.model_validate(job)
