"""Metrics computed on request from Penelope sensors."""

from fastapi import APIRouter, Depends

from orion_backend.schemas.derived_metric_schema import DerivedMetricResponse
from orion_backend.services.derived_metric_service import DerivedMetricService

router = APIRouter(tags=["derived-metrics"])


@router.get(
    "/derived-metrics",
    response_model=list[DerivedMetricResponse],
    summary="List derived metrics",
)
async def list_derived_metrics(
    service: DerivedMetricService = Depends(DerivedMetricService),
) -> list[DerivedMetricResponse]:
    """Every registered derived metric, with its unit."""
    return service.list_metrics()
