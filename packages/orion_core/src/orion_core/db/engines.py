"""Engine factories: async for the backend, sync for the pipeline and Alembic."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def _with_driver(url: str, driver: str) -> str:
    return make_url(url).set(drivername=driver).render_as_string(hide_password=False)


def make_async_engine(url: str, *, read_only: bool = False) -> AsyncEngine:
    server_settings = {"default_transaction_read_only": "on"} if read_only else {}
    return create_async_engine(
        _with_driver(url, "postgresql+asyncpg"),
        connect_args={"server_settings": server_settings},
    )


def make_sync_engine(url: str, *, read_only: bool = False) -> Engine:
    options = "-c default_transaction_read_only=on" if read_only else ""
    return create_engine(
        _with_driver(url, "postgresql+psycopg"), connect_args={"options": options}
    )
