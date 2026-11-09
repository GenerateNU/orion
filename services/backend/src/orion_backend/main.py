import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

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


def mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built frontend; unknown paths fall back to index.html for client-side routing."""

    # Explicit operation_id: generate_operation_id needs a tag, and this route has none.
    @app.get("/{path:path}", include_in_schema=False, operation_id="frontend")
    async def frontend(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist):
            return FileResponse(file)
        return FileResponse(dist / "index.html")


# Set in the all-in-one image (docker/orion.Dockerfile). Must be registered after the API routes.
if frontend_dist := os.getenv("FRONTEND_DIST"):
    mount_frontend(app, Path(frontend_dist).resolve())
