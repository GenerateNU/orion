"""Example vertical slice over Penelope (read-only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_penelope_db
from orion_backend.schemas.reading_schema import ReadingResponse
from orion_backend.services.reading_service import ReadingService

router = APIRouter(prefix="/runs/{run_id}/readings", tags=["readings"])


def get_reading_service(db: AsyncSession = Depends(get_penelope_db)) -> ReadingService:
    return ReadingService(db)


@router.get("", response_model=list[ReadingResponse], summary="List raw readings")
async def list_readings(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    limit: Annotated[int, Query(ge=1, le=1000, description="Max rows.")] = 100,
    service: ReadingService = Depends(get_reading_service),
) -> list[ReadingResponse]:
    """The first `limit` raw readings for a run, straight from Penelope."""
    return await service.list_readings(run_id, limit)
