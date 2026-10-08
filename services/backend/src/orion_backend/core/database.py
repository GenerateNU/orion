"""Async engines + per-request sessions for the two databases.

Transaction rule (from via-wms): `get_orion_db` commits once per request;
repositories only `flush()`. Penelope sessions never commit.
"""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orion_core.db.engines import make_async_engine
from orion_core.settings import Settings


def create_sessionmakers(settings: Settings) -> dict[str, async_sessionmaker]:
    makers = {"orion": async_sessionmaker(make_async_engine(settings.orion_database_url))}
    if settings.penelope_database_url:
        penelope = make_async_engine(settings.penelope_database_url, read_only=True)
        makers["penelope"] = async_sessionmaker(penelope)
    return makers


async def get_orion_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmakers["orion"]() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_penelope_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmakers["penelope"]() as session:
        yield session
