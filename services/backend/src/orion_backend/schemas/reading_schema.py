from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    time: datetime
    raw_tag: str = Field(description="Penelope dataTypeName.", examples=["VCU/CarState/speed"])
    values: list[float]
