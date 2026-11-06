from datetime import datetime

from sqlalchemy import INTEGER, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base


class Metrics(Base):
    """One row per lap of a run, written by the pipeline's lap step.

    Times are naive UTC, like the other trace tables.
    """

    __tablename__ = "metrics"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    lap_number: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    start_time: Mapped[datetime] = mapped_column("startTime", DateTime)
    end_time: Mapped[datetime] = mapped_column("endTime", DateTime)
