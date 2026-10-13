from datetime import datetime

from sqlalchemy import DateTime, String, UUID, ARRAY, FLOAT, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base

class CleanedData(Base):
    """Cleaned data for one Penelope run (`runId`): the pipeline's unit of work."""

    __tablename__ = "cleaned_data"

    run_id: Mapped[UUID] = mapped_column(UUID, primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    sensor: Mapped[str] = mapped_column(String, ForeignKey("sensors.sensor"), primary_key=True)
    values: Mapped[list[float]] = mapped_column(ARRAY(FLOAT))
