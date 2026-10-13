from datetime import datetime

from sqlalchemy import  String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from orion_core.models.orion.base import Base

class SensorSources(Base):
    """A mapping between Penelope sensor names and our cleaned sensor names."""

    __tablename__ = "sensor_sources"

    sourceDataTypeName: Mapped[str] = mapped_column(String, primary_key=True)
    sensor: Mapped[str] = mapped_column(String, ForeignKey("sensors.sensor"))
