"""The dashboard's graph tabs, in the frontend's `GraphTab` format (`graphViews.ts`)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_TABS = 50
MAX_GRAPHS_PER_TAB = 50


class GraphRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    channel: str = Field(min_length=1, max_length=200, description="Penelope `dataTypeName`.")


class GraphTabRequest(BaseModel):
    """One tab as saved. Strict, so a frontend bug can't write junk into the shared tabs."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100, pattern=r"\S")
    # Strict int, not Literal[1, 2]: pydantic can't make a Literal strict, and a lax one
    # accepts `true` as 1.
    layout: int = Field(strict=True, ge=1, le=2, description="Graph columns.")
    graphs: list[GraphRequest] = Field(max_length=MAX_GRAPHS_PER_TAB)


class GraphResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    channel: str


class GraphTabResponse(BaseModel):
    """One tab as loaded. Lenient, so tabs saved before a schema change still load."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    layout: Literal[1, 2]
    graphs: list[GraphResponse]
