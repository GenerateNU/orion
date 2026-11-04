"""Metrics computed on request from Penelope sensors."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_penelope_db
from orion_backend.core.openapi import error_responses
from orion_backend.schemas.derived_metric_schema import DerivedMetricResponse
from orion_backend.schemas.sensor_schema import SensorDataResponse
from orion_backend.services.derived_metric_service import DerivedMetricService
from orion_backend.services.sensor_service import SensorService

router = APIRouter(tags=["derived-metrics"])


def get_derived_metric_service(
    db: AsyncSession = Depends(get_penelope_db),
) -> DerivedMetricService:
    return DerivedMetricService(SensorService(db))


@router.get(
    "/derived-metrics",
    response_model=list[DerivedMetricResponse],
    summary="List derived metrics",
    responses=error_responses(503),
)
async def list_derived_metrics(
    service: DerivedMetricService = Depends(get_derived_metric_service),
) -> list[DerivedMetricResponse]:
    """Every registered derived metric, with its unit."""
    return service.list_metrics()


@router.get(
    "/runs/{run_id}/derived-metrics/{name:path}",
    response_model=SensorDataResponse,
    summary="Compute a derived metric",
    responses=error_responses(404, 422, 502, 503),
)
async def get_derived_metric_data(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    name: Annotated[str, Path(description="Name from `GET /derived-metrics`.")],
    start: Annotated[datetime, Query(description="Inclusive.")],
    end: Annotated[datetime, Query(description="Inclusive.")],
    service: DerivedMetricService = Depends(get_derived_metric_service),
) -> SensorDataResponse:
    """The metric computed from its input sensors between `start` and `end`, as one
    series keyed by `name`.
    """
    return await service.get_metric_data(run_id, name, start, end)
