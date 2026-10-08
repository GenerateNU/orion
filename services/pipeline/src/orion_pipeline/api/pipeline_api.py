from contextlib import asynccontextmanager

from fastapi import FastAPI

from orion_core.db.engines import make_sync_engine
from orion_core.settings import get_settings
from orion_pipeline.api.routes import pipeline_run_route
from orion_pipeline.jobs.job_queue import JobQueue


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.queue = JobQueue(make_sync_engine(get_settings().orion_database_url))
    yield


app = FastAPI(title="Orion Pipeline API", lifespan=lifespan)
app.include_router(pipeline_run_route.router)


@app.get("/health", tags=["health"])
def get_health() -> dict[str, str]:
    return {"status": "ok"}
