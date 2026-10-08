"""Example vertical slice over OrionDB: route → service → repository → model."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_orion_db
from orion_backend.core.openapi import error_responses
from orion_backend.schemas.run_schema import RunResponse
from orion_backend.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])


def get_run_service(db: AsyncSession = Depends(get_orion_db)) -> RunService:
    return RunService(db)


@router.get("", response_model=list[RunResponse], summary="List runs")
async def list_runs(service: RunService = Depends(get_run_service)) -> list[RunResponse]:
    """Every run OrionDB knows about."""
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
