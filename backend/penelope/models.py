from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DataType(BaseModel):
    """Mirrors a row in Penelope's `data_type` table."""
    name: str
    unit: Optional[str] = None


class DataPoint(BaseModel):
    """Mirrors a row in Penelope's `data` table."""
    dataTypeName: str
    time: datetime
    runId: str
    values: list[float]  