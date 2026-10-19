from fastapi import APIRouter

from orion_backend.routes import (
    health_route,
    penelope_run_route,
    pipeline_route,
    run_route,
    sensor_route,
    state_route,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_route.router)
api_router.include_router(run_route.router)
api_router.include_router(pipeline_route.router)
api_router.include_router(sensor_route.router)
api_router.include_router(penelope_run_route.router)
api_router.include_router(state_route.router)
