"""Read access to OrionDB for the API.

Route handlers ask for a connection with FastAPI's Depends(get_connection)
instead of opening one themselves, so there is one engine (and one connection
pool) for the whole app, every connection is closed when its request ends, and
tests can swap in their own database with app.dependency_overrides.

Failures are raised as Orion types, not SQLAlchemy ones, same contract as
repository.py. main.py turns them into HTTP responses.
"""

import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError

from .exceptions import OrionConfigError, OrionConnectionError


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Build the engine on first use, then reuse it.

    Built lazily rather than at import so the app (and CI) can start without
    NEON_DB_URL -- only the routes that actually need the database fail.

    Raises:
        OrionConfigError: NEON_DB_URL is missing or blank.
    """
    url = os.environ.get("NEON_DB_URL")
    if not url:
        raise OrionConfigError(
            "NEON_DB_URL is not set. Copy .env.example to .env in the repo root "
            "and paste your Neon connection string into it."
        )

    # Neon hands out plain postgresql:// URLs, and SQLAlchemy 2.1 maps those to
    # psycopg (v3), which isn't installed. Pin the driver we do ship, the same
    # one PenelopeClient names explicitly.
    for scheme in ("postgresql://", "postgres://"):
        if url.startswith(scheme):
            url = "postgresql+psycopg2://" + url.removeprefix(scheme)

    # Neon closes idle connections when its compute autosuspends, so a pooled
    # connection can be dead by the time a request picks it up. pre_ping checks
    # it first and quietly replaces it instead of failing the request.
    return create_engine(url, pool_pre_ping=True)


def get_connection() -> Iterator[Connection]:
    """FastAPI dependency: one connection per request, closed afterwards.

    Raises:
        OrionConfigError: NEON_DB_URL is missing or blank.
        OrionConnectionError: OrionDB could not be reached.
    """
    try:
        conn = get_engine().connect()
    except OperationalError as exc:
        raise OrionConnectionError(
            "Could not connect to OrionDB. Check NEON_DB_URL and that the Neon "
            "project is not paused."
        ) from exc

    with conn:
        yield conn # pauses the helper function so API code can run
