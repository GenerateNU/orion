"""Browse sessions: route → service → repository → model, over OrionDB."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_orion_db
from orion_backend.core.openapi import error_responses
from orion_backend.schemas.run_schema import (
    RunCreateRequest,
    RunResponse,
    RunUpdateRequest,
)
from orion_backend.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])


def get_run_service(db: AsyncSession = Depends(get_orion_db)) -> RunService:
    return RunService(db)


@router.get("", response_model=list[RunResponse], summary="List runs")
async def list_runs(
    service: RunService = Depends(get_run_service),
) -> list[RunResponse]:
    """Every run OrionDB knows about, newest first."""
    return await service.list_runs()


@router.get(
    "/{run_id}",
    response_model=RunResponse,
    summary="Get a run",
    responses=error_responses(404),
)
async def get_run(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    service: RunService = Depends(get_run_service),
) -> RunResponse:
    """One run by id. 404 if OrionDB has never seen it."""
    return await service.get_run(run_id)


@router.post(
    "",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a run",
    responses=error_responses(400),
)
async def create_run(
    body: RunCreateRequest, service: RunService = Depends(get_run_service)
) -> RunResponse:
    """Add a run to OrionDB. 400 if `run_id` already exists or `end_time` is before
    `start_time`."""
    return await service.create_run(body)


@router.patch(
    "/{run_id}",
    response_model=RunResponse,
    summary="Update a run's time bounds",
    responses=error_responses(400, 404),
)
async def update_run(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    body: RunUpdateRequest,
    service: RunService = Depends(get_run_service),
) -> RunResponse:
    """Set `start_time` and/or `end_time`. Fields left out of the body are unchanged.
    400 if the result has `end_time` before `start_time`."""
    return await service.update_run(run_id, body)


@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a run",
    responses=error_responses(400, 404),
)
async def delete_run(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    service: RunService = Depends(get_run_service),
) -> None:
    """Remove a run from OrionDB. 400 if pipeline jobs still reference it."""
    await service.delete_run(run_id)
