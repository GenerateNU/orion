from collections.abc import Collection, Sequence
from datetime import datetime

from sqlalchemy import Executable, Result, Row
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import UpstreamError
from orion_core.queries.penelope_queries import select_data_types, select_readings_between


class SensorRepository:
    """Reads Penelope through the shared query builders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_data_types(self) -> Sequence[Row]:
        return (await self._execute(select_data_types())).all()

    async def list_readings(
        self,
        run_id: str,
        data_type_names: Collection[str],
        start: datetime,
        end: datetime,
    ) -> Sequence[Row]:
        return (await self._execute(select_readings_between(run_id, data_type_names, start, end))).all()

    async def _execute(self, stmt: Executable) -> Result:
        # Handled differently because Penelope is externally managed. So it will call
        # Upstream service error instead of traditional failure.
        try:
            return await self.db.execute(stmt)
        except (OperationalError, InterfaceError, OSError) as exc:
            raise UpstreamError("Penelope", exc.__class__.__name__) from exc
