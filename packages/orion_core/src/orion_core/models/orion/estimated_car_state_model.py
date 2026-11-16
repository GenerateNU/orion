from datetime import datetime

from sqlalchemy import FLOAT, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base


class EstimatedCarState(Base):
    """Gets all fo the estimated car positions for one Penelope run (`runId`): the pipeline's unit of work."""

    __tablename__ = "estimated_car_state"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    lattitude: Mapped[float] = mapped_column(FLOAT)
    longitude: Mapped[float] = mapped_column(FLOAT)
    # 0-100 around the run's ideal lap, NULL off track. Written by lap_progress_step.
    # See docs/lap_progress.md.
    lap_percent: Mapped[float | None] = mapped_column(FLOAT, nullable=True)
