from fastapi import APIRouter

from orion_backend.routes import health_route, pipeline_route, reading_route, run_route

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_route.router)
api_router.include_router(run_route.router)
api_router.include_router(reading_route.router)
api_router.include_router(pipeline_route.router)
