from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class RunResponse(BaseModel):
    """A run (one session on the car) as listed by `GET /runs`."""

    model_config = ConfigDict(from_attributes=True)

    run_id: str = Field(
        description="Penelope run id. Used as `{run_id}` in every per-run route.",
        examples=["run-123"],
    )
    start_time: datetime | None = Field(
        description=(
            "Timestamp of the run's first reading (UTC). `null` until the pipeline's "
            "clean step has run."
        ),
        examples=["2026-10-01T14:02:11Z"],
    )
    end_time: datetime | None = Field(
        description=(
            "Timestamp of the run's last reading (UTC). `null` until the pipeline's "
            "clean step has run."
        ),
        examples=["2026-10-01T14:31:40Z"],
    )
    created_at: datetime = Field(
        description=(
            "When OrionDB first saw this run (`POST /runs`, or its first pipeline job "
            "was queued), not when it was driven."
        ),
        examples=["2026-10-02T09:00:00Z"],
    )

    # mypy can't type a decorator over @property; this is pydantic's documented fix.
    @computed_field(  # type: ignore[prop-decorator]
        description="`end_time - start_time` in seconds. `null` if either is `null`.",
        examples=[1769.0],
    )
    @property
    def duration_s(self) -> float | None:
        if self.start_time is None or self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()


# ----------------------------------------------------------------------------
# DEPRECATED: User currently has no reason to create or update run
# information. This is handled by pipeline
# ----------------------------------------------------------------------------
class RunCreateRequest(BaseModel):
    """Body of `POST /runs`. `created_at` is set by the database."""

    run_id: str = Field(
        min_length=1,
        description="Penelope run id. Must be unique.",
        examples=["run-123"],
    )
    start_time: datetime | None = Field(
        default=None,
        description="Timestamp of the run's first reading (UTC).",
        examples=["2026-10-01T14:02:11Z"],
    )
    end_time: datetime | None = Field(
        default=None,
        description="Timestamp of the run's last reading (UTC).",
        examples=["2026-10-01T14:31:40Z"],
    )


# ----------------------------------------------------------------------------
# DEPRECATED: User currently has no reason to create or update run
# information. This is handled by pipeline
# ----------------------------------------------------------------------------
class RunUpdateRequest(BaseModel):
    """Body of `PATCH /runs/{run_id}`. Only the fields sent are changed; send
    `null` to clear one."""

    start_time: datetime | None = Field(
        default=None,
        description="Timestamp of the run's first reading (UTC).",
        examples=["2026-10-01T14:02:11Z"],
    )
    end_time: datetime | None = Field(
        default=None,
        description="Timestamp of the run's last reading (UTC).",
        examples=["2026-10-01T14:31:40Z"],
    )
