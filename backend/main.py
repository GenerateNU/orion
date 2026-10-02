from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

from controllers.race_controller import router as race_router
from orion.db import get_connection
from orion.exceptions import OrionConfigError, OrionConnectionError, OrionSchemaError

app = FastAPI(title="orion")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tell FastAPI to use the router we created in the race_controller.py file.
app.include_router(race_router)


# Turn OrionDB failures into clean JSON errors instead of a bare 500 traceback.
# 503 = the database is down/asleep, worth retrying; 500 = the server is
# misconfigured or the schema is missing, someone has to fix it.
@app.exception_handler(OrionConnectionError)
def orion_connection_error(_request: Request, exc: OrionConnectionError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(OrionConfigError)
def orion_config_error(_request: Request, exc: OrionConfigError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# Connected, but the query failed -- e.g. setup_orion.py hasn't created the tables.
@app.exception_handler(OrionSchemaError)
def orion_schema_error(_request: Request, exc: OrionSchemaError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Proves the API can actually reach OrionDB, separate from /api/health so the
# plain health check still works when the database is down.
@app.get("/api/health/db")
def health_db(conn: Annotated[Connection, Depends(get_connection)]):
    try:
        conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        raise OrionConnectionError("Lost connection to OrionDB mid-query.") from exc
    return {"database": "ok"}
