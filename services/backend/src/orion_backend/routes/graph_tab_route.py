"""The dashboard's graph tabs: one list shared by the whole team, the same for every run."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_orion_db
from orion_backend.core.openapi import error_responses
from orion_backend.schemas.graph_tab_schema import MAX_TABS, GraphTabRequest, GraphTabResponse
from orion_backend.services.graph_tab_service import GraphTabService

router = APIRouter(prefix="/graph-tabs", tags=["graph-tabs"])


def get_graph_tab_service(db: AsyncSession = Depends(get_orion_db)) -> GraphTabService:
    return GraphTabService(db)


@router.get("", response_model=list[GraphTabResponse], summary="Get graph tabs")
async def get_graph_tabs(
    service: GraphTabService = Depends(get_graph_tab_service),
) -> list[dict[str, Any]]:
    """Every saved tab in tab-bar order, or `[]` if none have been saved."""
    return await service.get_tabs()


@router.put(
    "",
    response_model=list[GraphTabResponse],
    summary="Save graph tabs",
    responses=error_responses(422),
)
async def save_graph_tabs(
    tabs: Annotated[list[GraphTabRequest], Body(max_length=MAX_TABS)],
    service: GraphTabService = Depends(get_graph_tab_service),
) -> list[GraphTabRequest]:
    """Replace every saved tab with `tabs`. The last save wins. 422 on duplicate tab
    or graph ids."""
    return await service.save_tabs(tabs)
