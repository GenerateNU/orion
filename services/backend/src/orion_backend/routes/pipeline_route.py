from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status

from orion_backend.services.pipeline_service import PipelineService
from orion_core.schemas.pipeline_run_schema import PipelineRunCreate, PipelineRunResponse

router = APIRouter(prefix="/pipeline/runs", tags=["pipeline"])


def get_pipeline_service(request: Request) -> PipelineService:
    return PipelineService(request.app.state.pipeline_http)


@router.post(
    "",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue a pipeline job",
)
async def create_pipeline_run(
    body: PipelineRunCreate, service: PipelineService = Depends(get_pipeline_service)
) -> PipelineRunResponse:
    """Asks the pipeline service to process a run. Returns once the job is queued."""
    return await service.trigger(body)


@router.get("/{pipeline_run_id}", response_model=PipelineRunResponse, summary="Get a pipeline job")
async def get_pipeline_run(
    pipeline_run_id: Annotated[int, Path(description="Pipeline job id.")],
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineRunResponse:
    """A job's current status.

    TODO: add `GET /{id}/events` to stream progress (Server-Sent Events).
    """
    return await service.get(pipeline_run_id)
