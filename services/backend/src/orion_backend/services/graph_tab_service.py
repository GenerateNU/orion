from collections import Counter
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import InvalidParameterError
from orion_backend.repositories.graph_tab_repository import GraphTabRepository
from orion_backend.schemas.graph_tab_schema import GraphTabRequest


class GraphTabService:
    """The team's shared graph tabs. Each save replaces the whole list."""

    def __init__(self, db: AsyncSession):
        self.repository = GraphTabRepository(db)

    async def get_tabs(self) -> list[dict[str, Any]]:
        return await self.repository.get_tabs() or []

    async def save_tabs(self, tabs: list[GraphTabRequest]) -> list[GraphTabRequest]:
        _check_unique("tab", [tab.id for tab in tabs])
        # The frontend finds graphs by id across all tabs, not just within one.
        _check_unique("graph", [graph.id for tab in tabs for graph in tab.graphs])
        await self.repository.save_tabs([tab.model_dump() for tab in tabs])
        return tabs


def _check_unique(kind: str, ids: list[str]) -> None:
    duplicates = sorted(id_ for id_, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise InvalidParameterError(f"Duplicate {kind} ids: {', '.join(duplicates)}")
