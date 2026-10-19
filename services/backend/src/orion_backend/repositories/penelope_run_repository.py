from collections.abc import Collection, Sequence
from typing import Any

from sqlalchemy import Executable, Result, Row
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import UpstreamError
from orion_core.queries.penelope_queries import (
    select_penelope_runs,
    select_penelope_runs_by_ids,
)


class PenelopeRunRepository:
    """Reads Penelope's `run` table through the shared query builders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_runs(self) -> Sequence[Row[*tuple[Any, ...]]]:
        return (await self._execute(select_penelope_runs())).all()

    async def list_runs_by_ids(
        self, run_ids: Collection[str]
    ) -> Sequence[Row[*tuple[Any, ...]]]:
        return (await self._execute(select_penelope_runs_by_ids(run_ids))).all()

    async def _execute(self, stmt: Executable) -> Result[*tuple[Any, ...]]:
        # Penelope is externally managed, so a failure is an upstream error (502).
        try:
            return await self.db.execute(stmt)
        except (OperationalError, InterfaceError, OSError) as exc:
            raise UpstreamError("Penelope", exc.__class__.__name__) from exc
