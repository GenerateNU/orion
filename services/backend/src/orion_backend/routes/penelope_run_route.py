"""Runs recorded in Penelope, for picking one to send through the pipeline."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_orion_db, get_penelope_db
from orion_backend.core.openapi import error_responses
from orion_backend.schemas.penelope_run_schema import PenelopeRunResponse
from orion_backend.services.penelope_run_service import PenelopeRunService

router = APIRouter(prefix="/penelope/runs", tags=["penelope"])


def get_penelope_run_service(
    penelope_db: AsyncSession = Depends(get_penelope_db),
    orion_db: AsyncSession = Depends(get_orion_db),
) -> PenelopeRunService:
    return PenelopeRunService(penelope_db, orion_db)


@router.get(
    "",
    response_model=list[PenelopeRunResponse],
    summary="List Penelope runs",
    responses=error_responses(502, 503),
)
async def list_penelope_runs(
    service: PenelopeRunService = Depends(get_penelope_run_service),
) -> list[PenelopeRunResponse]:
    """Every run in Penelope's `run` table, newest first. `processed` marks runs Orion
    has already processed (they can still be processed again)."""
    return await service.list_runs()
