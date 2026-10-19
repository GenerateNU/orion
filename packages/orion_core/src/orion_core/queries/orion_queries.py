"""OrionDB statement builders. They build statements but never run them, so the
async backend and the sync pipeline can share them."""

from datetime import datetime
from typing import Any

from sqlalchemy import Select, delete, exists, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql.dml import ReturningDelete, ReturningInsert, ReturningUpdate

from orion_core.models.orion import (
    EstimatedCarState,
    PipelineRun,
    PipelineStatus,
    Run,
    SensorSources,
)


def select_sensor_sources() -> Select[*tuple[Any, ...]]:
    """Every Penelope tag we know how to map, and the generic sensor it maps to."""
    return select(
        SensorSources.source_data_type_name.label("raw_tag"),
        SensorSources.sensor,
    )


def select_estimated_positions_between(
    run_id: str, start: datetime, end: datetime
) -> Select[datetime, float, float]:
    """Estimated (lat, lon) for one run in [start, end], ordered by time."""
    return (
        select(
            EstimatedCarState.time,
            EstimatedCarState.lattitude,
            EstimatedCarState.longitude,
        )
        .where(
            EstimatedCarState.run_id == run_id,
            EstimatedCarState.time.between(start, end),
        )
        .order_by(EstimatedCarState.time)
    )


def select_runs() -> Select[Run]:
    """Every run, newest drive first."""
    return select(Run).order_by(Run.start_time.desc(), Run.run_id)


def select_processed_run_ids() -> Select[str]:
    """Ids of runs with at least one pipeline job that succeeded without an error."""
    return (
        select(PipelineRun.run_id)
        .where(
            PipelineRun.status == PipelineStatus.SUCCEEDED,
            PipelineRun.error.is_(None),
        )
        .distinct()
    )


def select_processed_runs() -> Select[Run]:
    """`select_runs`, limited to processed runs (see `select_processed_run_ids`)."""
    return select_runs().where(Run.run_id.in_(select_processed_run_ids()))


def select_pipeline_runs(
    run_id: str | None = None, status: str | None = None, limit: int = 50
) -> Select[PipelineRun]:
    """Pipeline jobs, newest first, optionally for one run and/or one status."""
    stmt = select(PipelineRun).order_by(
        PipelineRun.queued_at.desc(), PipelineRun.id.desc()
    )
    if run_id is not None:
        stmt = stmt.where(PipelineRun.run_id == run_id)
    if status is not None:
        stmt = stmt.where(PipelineRun.status == status)
    return stmt.limit(limit)


def select_active_pipeline_run(run_id: str) -> Select[PipelineRun]:
    """The run's queued or running job, if it has one."""
    return (
        select(PipelineRun)
        .where(
            PipelineRun.run_id == run_id,
            PipelineRun.status.in_([PipelineStatus.QUEUED, PipelineStatus.RUNNING]),
        )
        .limit(1)
    )


def select_run(run_id: str) -> Select[Run]:
    """One run by id."""
    return select(Run).where(Run.run_id == run_id)


def select_run_has_pipeline_runs(run_id: str) -> Select[bool]:
    """Whether any pipeline job references the run (its FK blocks a delete)."""
    return select(exists().where(PipelineRun.run_id == run_id))


def insert_run(
    run_id: str, start_time: datetime | None, end_time: datetime | None
) -> ReturningInsert[Run]:
    """Create a run, returning it. Returns no row if `run_id` already exists."""
    return (
        insert(Run)
        .values(run_id=run_id, start_time=start_time, end_time=end_time)
        .on_conflict_do_nothing(index_elements=[Run.run_id])
        .returning(Run)
    )


def update_run(run_id: str, **values: datetime | None) -> ReturningUpdate[Run]:
    """Set the given columns on a run, returning it. Returns no row if it doesn't exist."""
    return update(Run).where(Run.run_id == run_id).values(**values).returning(Run)


def delete_run(run_id: str) -> ReturningDelete[str]:
    """Delete a run, returning its id. Returns no row if it doesn't exist."""
    return delete(Run).where(Run.run_id == run_id).returning(Run.run_id)
