from datetime import datetime

from sqlalchemy import DateTime, String, func, ARRAY, FLOAT, INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base

class EstimatedCarState(Base):
    """Gets all fo the estimated car positions for one Penelope run (`runId`): the pipeline's unit of work."""

    __tablename__ = "estimated_car_state"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    lattitude: Mapped[float] = mapped_column(FLOAT)
    longitude: Mapped[float] = mapped_column(FLOAT)