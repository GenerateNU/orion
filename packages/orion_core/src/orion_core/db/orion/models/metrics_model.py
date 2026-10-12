from datetime import datetime

from sqlalchemy import DateTime, UUID, INTEGER, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.db.orion.base import Base


class Metrics(Base):
    """Metrics for one Penelope run (`runId`): the pipeline's unit of work."""

    __tablename__ = "metrics"

    run_id: Mapped[UUID] = mapped_column(UUID, primary_key=True)
    lap_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("estimated_car_state.lap_id"))
    startTime: Mapped[datetime] = mapped_column(DateTime)
    endTime: Mapped[datetime] = mapped_column(DateTime)