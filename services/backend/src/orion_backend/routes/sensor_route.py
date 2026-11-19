"""Raw sensor data straight from Penelope (read-only), for debugging what the car sent."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_orion_db, get_penelope_db
from orion_backend.core.openapi import error_responses
from orion_backend.schemas.sensor_schema import SensorDataResponse, SensorResponse
from orion_backend.services.sensor_service import SensorService

router = APIRouter(tags=["sensors"])


def get_sensor_service(
    penelope_db: AsyncSession = Depends(get_penelope_db),
    orion_db: AsyncSession = Depends(get_orion_db),
) -> SensorService:
    return SensorService(penelope_db, orion_db)


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
    # Leaves `lap_id` / `lap_percent` out entirely unless they were asked for.
    response_model_exclude_unset=True,
    summary="Get raw sensor readings",
    responses=error_responses(404, 422, 502, 503),
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


@router.get(
    "/runs/{run_id}/laps/sensors/data",
    response_model=list[SensorDataResponse],
    summary="Get sensor readings by lap percent",
    responses=error_responses(404, 422, 502, 503),
)
async def get_lap_sensor_data(
    run_id: Annotated[str, Path(description="Penelope run id.")],
    sensors: Annotated[
        str,
        Query(
            description="Comma-separated Penelope `dataTypeName`s.",
            examples=["TPU/GPS/GroundSpeed,BMS/Pack/SoC"],
        ),
    ],
    lap_ids: Annotated[list[int], Query(description="Repeat for each lap.")],
    start_percent: Annotated[float, Query(description="Inclusive.")] = 0,
    end_percent: Annotated[float, Query(description="Inclusive.")] = 100,
    service: SensorService = Depends(get_sensor_service),
) -> list[SensorDataResponse]:
    """For each lap in `lap_ids` (e.g. `?lap_ids=3&lap_ids=5`), every reading of the
    requested sensors while that lap was between `start_percent` and `end_percent`
    (the whole lap by default). One response per lap, in the order given, with
    `lap_id` and `lap_percent` lined up with each series' `time`.

    A lap with no positions in the percent range is a 404 (e.g. the pipeline hasn't
    processed the run, or it has fewer than 3 laps).
    """
    names = [name.strip() for name in sensors.split(",") if name.strip()]
    return [
        await service.get_sensor_data(
            run_id,
            names,
            lap_id=lap_id,
            start_percent=start_percent,
            end_percent=end_percent,
        )
        for lap_id in lap_ids
    ]
