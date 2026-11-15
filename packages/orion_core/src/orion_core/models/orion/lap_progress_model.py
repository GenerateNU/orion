from datetime import datetime

from sqlalchemy import FLOAT, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base


class LapProgress(Base):
    """How far around the run's ideal lap the car is at each estimated position.

    Written by the lap progress step, one row per `estimated_car_state` row.
    See docs/lap_progress.md.
    """

    __tablename__ = "lap_progress"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    # The `laps` row this point falls in.
    lap_id: Mapped[int] = mapped_column(Integer)
    # 0 to 100, measured along the run's ideal lap. NULL when the car is off track
    # (pits, spins, stopped).
    lap_percent: Mapped[float | None] = mapped_column(FLOAT, nullable=True)


class IdealLapPoint(Base):
    """One point of a run's ideal lap, the path every lap percentage is measured
    along. Written by the lap progress step. See docs/ideal_lap.md."""

    __tablename__ = "ideal_lap_points"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    # Order along the path, from 0 at the start/finish gate.
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    latitude: Mapped[float] = mapped_column(FLOAT)
    longitude: Mapped[float] = mapped_column(FLOAT)
    lap_percent: Mapped[float] = mapped_column(FLOAT)
