"""Estimated car state for a run, from OrionDB `estimated_car_state` (read-only)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_orion_db
from orion_backend.core.openapi import error_responses
from orion_backend.schemas.state_schema import StateDataResponse
from orion_backend.services.state_service import StateService

router = APIRouter(tags=["state"])


def get_state_service(db: AsyncSession = Depends(get_orion_db)) -> StateService:
    return StateService(db)


@router.get(
    "/runs/{run_id}/state",
    response_model=StateDataResponse,
    summary="Get estimated car positions",
    responses=error_responses(422),
)
async def get_state_data(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    start: Annotated[datetime, Query(description="Inclusive.")],
    end: Annotated[datetime, Query(description="Inclusive.")],
    service: StateService = Depends(get_state_service),
) -> StateDataResponse:
    """Every estimated `[lat, lon]` position between `start` and `end`, with no
    downsampling.

    The time bounds are required so a request can't pull a whole run. An unknown run
    or a range with no rows comes back with empty lists.
    """
    # Strip timezone from query params (DB column is TIMESTAMP WITHOUT TIME ZONE)
    start_naive = start.replace(tzinfo=None) if start.tzinfo else start
    end_naive = end.replace(tzinfo=None) if end.tzinfo else end
    
    return await service.get_state_data(run_id, start_naive, end_naive)