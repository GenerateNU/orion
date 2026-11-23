from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import (
    AlreadyExistsError,
    DomainError,
    NotFoundError,
    ServiceUnavailableError,
)
from orion_backend.repositories.penelope_run_repository import PenelopeRunRepository
from orion_backend.repositories.run_repository import RunRepository
from orion_backend.schemas.run_schema import (
    RunCreateRequest,
    RunResponse,
    RunSyncResponse,
    RunUpdateRequest,
)
from orion_core.models.orion import Run


class RunService:
    """Business rules live here: e.g. turning "no row" into a NotFoundError."""

    def __init__(self, db: AsyncSession, penelope_db: AsyncSession | None = None):
        self.repository = RunRepository(db)
        self.penelope_repository = (
            PenelopeRunRepository(penelope_db) if penelope_db is not None else None
        )

    async def list_runs(self, processed: bool = False) -> list[RunResponse]:
        """Every run (or only processed ones), read from OrionDB alone. `run_time` is
        whatever the last Penelope sync stored."""
        runs = await (
            self.repository.list_processed_runs()
            if processed
            else self.repository.list_runs()
        )
        processed_ids = await self.repository.list_processed_run_ids()
        return [_to_response(run, processed_ids) for run in runs]

    async def sync_from_penelope(self) -> RunSyncResponse:
        """Copy every Penelope run (id and `run.time`) into OrionDB. Safe to repeat:
        new runs are added, existing ones only get `run_time` refreshed."""
        if self.penelope_repository is None:
            raise ServiceUnavailableError(
                "Penelope is not configured (PENELOPE_DATABASE_URL unset)"
            )
        penelope_runs = [
            (str(row.run_id), row.time)
            for row in await self.penelope_repository.list_runs()
        ]
        existing = await self.repository.list_run_ids()
        changed = await self.repository.upsert_run_times(penelope_runs)
        return RunSyncResponse(
            total=len(penelope_runs),
            added=len(changed - existing),
            updated=len(changed & existing),
        )

    async def get_run(self, run_id: str) -> RunResponse:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise NotFoundError("Run", run_id)
        return _to_response(run, await self.repository.list_processed_run_ids())

    # ------------------------------------------------------------------------
    # DEPRECATED: User currently has no reason to create or update run
    # information. This is handled by pipeline
    # ------------------------------------------------------------------------
    async def create_run(self, body: RunCreateRequest) -> RunResponse:
        _check_bounds(body.start_time, body.end_time)
        run = await self.repository.create_run(
            body.run_id, body.start_time, body.end_time
        )
        if run is None:
            raise AlreadyExistsError("Run", body.run_id)
        return RunResponse.model_validate(run)

    # ------------------------------------------------------------------------
    # DEPRECATED: User currently has no reason to create or update run
    # information. This is handled by pipeline
    # ------------------------------------------------------------------------
    async def update_run(self, run_id: str, body: RunUpdateRequest) -> RunResponse:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise NotFoundError("Run", run_id)
        values = body.model_dump(exclude_unset=True)
        if not values:
            return RunResponse.model_validate(run)
        _check_bounds(
            values.get("start_time", run.start_time),
            values.get("end_time", run.end_time),
        )
        return RunResponse.model_validate(
            await self.repository.update_run(run_id, **values)
        )

    async def delete_run(self, run_id: str) -> None:
        if await self.repository.has_pipeline_runs(run_id):
            raise DomainError(f"Run '{run_id}' has pipeline jobs and cannot be deleted")
        if not await self.repository.delete_run(run_id):
            raise NotFoundError("Run", run_id)


def _to_response(run: Run, processed_ids: set[str]) -> RunResponse:
    return RunResponse.model_validate(run).model_copy(
        update={"processed": run.run_id in processed_ids}
    )


def _check_bounds(start_time: datetime | None, end_time: datetime | None) -> None:
    if start_time is not None and end_time is not None and end_time < start_time:
        raise DomainError("end_time must not be before start_time")
