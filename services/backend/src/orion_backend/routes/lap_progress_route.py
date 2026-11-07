"""Lap progress for a run, from OrionDB `laps` and `estimated_car_state` (read-only)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_orion_db
from orion_backend.core.openapi import error_responses
from orion_backend.schemas.lap_progress_schema import LapProgressResponse
from orion_backend.services.lap_progress_service import LapProgressService

router = APIRouter(tags=["laps"])


def get_lap_progress_service(
    db: AsyncSession = Depends(get_orion_db),
) -> LapProgressService:
    return LapProgressService(db)


@router.get(
    "/runs/{run_id}/laps/progress",
    response_model=LapProgressResponse,
    summary="Get lap progress",
    responses=error_responses(404, 422),
)
async def get_lap_progress(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    start: Annotated[datetime, Query(description="Inclusive.")],
    end: Annotated[datetime, Query(description="Inclusive.")],
    service: LapProgressService = Depends(get_lap_progress_service),
) -> LapProgressResponse:
    """How far through its lap the car is, from 0 to 1, at every estimated position
    between `start` and `end` that falls in a lap.

    A range with no rows comes back with empty lists. A run with no laps (including
    an unknown run), or whose reference lap has no positions, is a 404.
    """
    return await service.get_lap_progress(run_id, start, end)
