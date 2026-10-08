from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str = Field(description="Human-readable error message.")
    resource_type: str | None = Field(default=None, description="404 only.")
    resource_id: str | None = Field(default=None, description="404 only.")
