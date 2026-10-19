from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import FastAPI

from orion_backend.api import api_router
from orion_backend.core.database import create_engines, create_sessionmakers
from orion_backend.core.exception_handlers import register_exception_handlers
from orion_backend.core.openapi import TAGS_METADATA, generate_operation_id
from orion_core.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    settings = get_settings()
    engines = create_engines(settings)
    app.state.sessionmakers = create_sessionmakers(engines)
    app.state.pipeline_http = httpx.AsyncClient(base_url=settings.pipeline_api_url)
    try:
        yield
    finally:
        # Close DB connections
        await app.state.pipeline_http.aclose()
        for engine in engines.values():
            await engine.dispose()


app = FastAPI(
    title="Orion API",
    openapi_tags=TAGS_METADATA,
    generate_unique_id_function=generate_operation_id,
    lifespan=lifespan,
)
register_exception_handlers(app)
app.include_router(api_router)
