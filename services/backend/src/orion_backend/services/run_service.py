import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import (
    AlreadyExistsError,
    DomainError,
    NotFoundError,
    UpstreamError,
)
from orion_backend.repositories.penelope_run_repository import PenelopeRunRepository
from orion_backend.repositories.run_repository import RunRepository
from orion_backend.schemas.run_schema import (
    RunCreateRequest,
    RunResponse,
    RunUpdateRequest,
)


logger = logging.getLogger(__name__)

# Penelope run times are a nice-to-have on the run list. Off VPN a connect attempt can
# hang for a long time, so give up quickly and return the list without them.
PENELOPE_LABEL_TIMEOUT_S = 3


class RunService:
    """Business rules live here: e.g. turning "no row" into a NotFoundError."""

    def __init__(self, db: AsyncSession, penelope_db: AsyncSession | None = None):
        self.repository = RunRepository(db)
        self.penelope_repository = (
            PenelopeRunRepository(penelope_db) if penelope_db is not None else None
        )

    async def list_runs(self, processed: bool = False) -> list[RunResponse]:
        """Every run (or only processed ones), labelled from Penelope when reachable."""
        runs = await (
            self.repository.list_processed_runs()
            if processed
            else self.repository.list_runs()
        )
        return await self._with_penelope_labels(
            [RunResponse.model_validate(run) for run in runs]
        )

    async def _with_penelope_labels(self, runs: list[RunResponse]) -> list[RunResponse]:
        """Fill `run_time` from Penelope. Leaves it `null` if Penelope isn't
        configured, is unreachable, or doesn't answer in time."""
        if self.penelope_repository is None or not runs:
            return runs
        try:
            async with asyncio.timeout(PENELOPE_LABEL_TIMEOUT_S):
                rows = await self.penelope_repository.list_runs_by_ids(
                    [run.run_id for run in runs]
                )
        except (UpstreamError, TimeoutError) as exc:
            logger.warning("listing runs without Penelope labels: %r", exc)
            return runs
        times = {row.run_id: row.time for row in rows}
        return [
            run.model_copy(update={"run_time": times[run.run_id]})
            if run.run_id in times
            else run
            for run in runs
        ]

    async def get_run(self, run_id: str) -> RunResponse:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise NotFoundError("Run", run_id)
        return RunResponse.model_validate(run)

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


def _check_bounds(start_time: datetime | None, end_time: datetime | None) -> None:
    if start_time is not None and end_time is not None and end_time < start_time:
        raise DomainError("end_time must not be before start_time")
