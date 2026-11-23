from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orion_core.queries.orion_queries import select_graph_tabs, upsert_graph_tabs


class GraphTabRepository:
    """OrionDB `graph_tabs` through the shared query builders. Never commits."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tabs(self) -> list[dict[str, Any]] | None:
        """None if nothing has been saved yet."""
        
        tabs: list[dict[str, Any]] | None = await self.db.scalar(select_graph_tabs())
        return tabs

    async def save_tabs(self, tabs: list[dict[str, Any]]) -> None:
        await self.db.execute(upsert_graph_tabs(tabs))
