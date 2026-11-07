from datetime import datetime

from sqlalchemy import ARRAY, FLOAT, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base


class UkfState(Base):
    """The forward UKF pass for one run, one row per 10ms tick. Read by the RTS step.

    Arrays are flattened row-major: x and x_pred hold 6 values, p, p_pred and
    cross_cov hold 36. The prediction columns are NULL on ticks where the filter
    (re)started. x/y meters are measured from (origin_lat, origin_lon).
    """

    __tablename__ = "ukf_states"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    origin_lat: Mapped[float] = mapped_column(FLOAT)
    origin_lon: Mapped[float] = mapped_column(FLOAT)
    x: Mapped[list[float]] = mapped_column(ARRAY(FLOAT))
    p: Mapped[list[float]] = mapped_column(ARRAY(FLOAT))
    x_pred: Mapped[list[float] | None] = mapped_column(ARRAY(FLOAT), nullable=True)
    p_pred: Mapped[list[float] | None] = mapped_column(ARRAY(FLOAT), nullable=True)
    cross_cov: Mapped[list[float] | None] = mapped_column(ARRAY(FLOAT), nullable=True)
