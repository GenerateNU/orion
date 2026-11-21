from datetime import datetime

from sqlalchemy import FLOAT, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base


class LapProgress(Base):
    """How far round the lap each estimated position of one run was. Written by
    the lap progress step, one row per `estimated_car_state` row.
    See docs/lap_progress.md."""

    __tablename__ = "lap_progress"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    # The `laps` row this position falls in.
    lap_id: Mapped[int] = mapped_column(Integer)
    # 0-100 around the run's ideal lap, NULL off track.
    lap_percent: Mapped[float | None] = mapped_column(FLOAT, nullable=True)
