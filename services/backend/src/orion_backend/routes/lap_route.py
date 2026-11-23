"""Laps for a run, from OrionDB `laps` (read-only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_orion_db
from orion_backend.schemas.lap_schema import LapsResponse
from orion_backend.services.lap_service import LapService

router = APIRouter(tags=["laps"])


def get_lap_service(db: AsyncSession = Depends(get_orion_db)) -> LapService:
    return LapService(db)


@router.get("/runs/{run_id}/laps", response_model=LapsResponse, summary="List laps")
async def list_laps(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    service: LapService = Depends(get_lap_service),
) -> LapsResponse:
    """Every lap of the run, in order. An unknown run, or one the pipeline hasn't
    processed, comes back with an empty list."""
    return await service.get_laps(run_id)
