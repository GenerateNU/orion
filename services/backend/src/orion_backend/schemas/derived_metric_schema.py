"""Metrics computed on request from Penelope sensors."""

from pydantic import BaseModel, Field


class DerivedMetricResponse(BaseModel):
    """One registered derived metric."""

    name: str = Field(description="Unique metric name.", examples=["regen/power"])
    unit: str = Field(description="Unit of the metric's values.", examples=["W"])
