from datetime import datetime

from sqlalchemy import DateTime, String, func, UUID, ARRAY, FLOAT
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base

class Sensors(Base):
    """Our sensor names along with the unit that they are in, unit is NULL if the sensor is unitless."""

    __tablename__ = "sensors"

    sensor: Mapped[str] = mapped_column(String, primary_key=True)
    unit: Mapped[str] = mapped_column(String)