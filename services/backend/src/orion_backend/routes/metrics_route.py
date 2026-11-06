"""Laps for a run, from OrionDB `metrics` (read-only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_orion_db
from orion_backend.core.openapi import error_responses
from orion_backend.schemas.metrics_schema import MetricsResponse
from orion_backend.services.metrics_service import MetricsService

router = APIRouter(tags=["metrics"])


def get_metrics_service(db: AsyncSession = Depends(get_orion_db)) -> MetricsService:
    return MetricsService(db)


@router.get(
    "/runs/{run_id}/metrics",
    response_model=MetricsResponse,
    summary="Get laps",
    responses=error_responses(422),
)
async def get_metrics(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    service: MetricsService = Depends(get_metrics_service),
) -> MetricsResponse:
    """Every lap for the run, ordered by lap number. An unknown run or a run with no laps
    comes back with an empty list."""
    return await service.get_metrics(run_id)
