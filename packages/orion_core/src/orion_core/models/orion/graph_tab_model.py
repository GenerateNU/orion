from typing import Any

from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base


class GraphTab(Base):
    """The dashboard's graph tabs, shared by the whole team. A single row (`id` 1)
    holding the frontend's `GraphTab[]` list in tab-bar order."""

    __tablename__ = "graph_tabs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    tabs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
