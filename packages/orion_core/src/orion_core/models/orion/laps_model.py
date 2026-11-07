from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base


class Lap(Base):
    """One detected lap of one Penelope run. Written by the lap step."""

    __tablename__ = "laps"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    # Assigned by the lap step, starting at 1 for every run.
    lap_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
