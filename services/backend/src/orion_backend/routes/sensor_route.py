"""Raw sensor data straight from Penelope (read-only), for debugging what the car sent."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_penelope_db
from orion_backend.core.openapi import error_responses
from orion_backend.schemas.sensor_schema import SensorDataResponse, SensorResponse
from orion_backend.services.sensor_service import SensorService

router = APIRouter(tags=["sensors"])


def get_sensor_service(db: AsyncSession = Depends(get_penelope_db)) -> SensorService:
    return SensorService(db)


@router.get(
    "/sensors",
    response_model=list[SensorResponse],
    summary="List sensor types",
    responses=error_responses(502, 503),
)
async def list_sensors(
    service: SensorService = Depends(get_sensor_service),
) -> list[SensorResponse]:
    """Every sensor type in Penelope's `data_type` table, with its unit."""
    return await service.list_sensors()


@router.get(
    "/runs/{run_id}/sensors/data",
    response_model=SensorDataResponse,
    summary="Get raw sensor readings",
    responses=error_responses(422, 502, 503),
)
async def get_sensor_data(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    sensors: Annotated[
        str,
        Query(
            description="Comma-separated Penelope `dataTypeName`s.",
            examples=["TPU/GPS/Location,BMS/Pack/SoC"],
        ),
    ],
    start: Annotated[datetime, Query(description="Inclusive.")],
    end: Annotated[datetime, Query(description="Inclusive.")],
    service: SensorService = Depends(get_sensor_service),
) -> SensorDataResponse:
    """Every reading of the requested sensors between `start` and `end`, as stored in
    Penelope, with no downsampling.

    The time bounds are required so a request can't pull a whole run. A sensor with no
    rows in the range (or an unknown run) comes back as an empty series.
    """
    names = [name.strip() for name in sensors.split(",") if name.strip()]
    return await service.get_sensor_data(run_id, names, start, end)
