import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from orion_backend.core.exceptions import ServiceUnavailableError
from orion_backend.services.run_service import RunService
from orion_core.queries.orion_queries import upsert_run_times

T1 = datetime(2026, 7, 11, 16, 42, 18, tzinfo=UTC)
T2 = datetime(2026, 7, 12, 9, 0, 0, tzinfo=UTC)


class FakeRunRepository:
    def __init__(self, existing: set[str], changed: set[str]):
        self.existing = existing
        self.changed = changed
        self.upserted: list[tuple[str, datetime | None]] | None = None

    async def list_run_ids(self) -> set[str]:
        return self.existing

    async def upsert_run_times(self, rows):
        self.upserted = rows
        return self.changed


class FakePenelopeRepository:
    def __init__(self, rows):
        self.rows = rows

    async def list_runs(self):
        return self.rows


def make_service(penelope_rows, existing, changed) -> Any:
    service: Any = RunService.__new__(RunService)
    service.repository = FakeRunRepository(existing, changed)
    service.penelope_repository = FakePenelopeRepository(penelope_rows)
    return service


def test_sync_counts_added_and_updated():
    rows = [
        SimpleNamespace(run_id="a", time=T1),  # new
        SimpleNamespace(run_id="b", time=T2),  # existing, run_time changed
        SimpleNamespace(run_id="c", time=None),  # existing, unchanged
    ]
    service = make_service(rows, existing={"b", "c"}, changed={"a", "b"})

    result = asyncio.run(service.sync_from_penelope())

    assert (result.total, result.added, result.updated) == (3, 1, 1)
    assert service.repository.upserted == [("a", T1), ("b", T2), ("c", None)]


def test_sync_without_penelope_is_unavailable():
    service = make_service([], existing=set(), changed=set())
    service.penelope_repository = None
    with pytest.raises(ServiceUnavailableError):
        asyncio.run(service.sync_from_penelope())


def test_upsert_only_touches_run_time():
    sql = str(
        upsert_run_times([("a", T1)]).compile(dialect=postgresql.dialect())
    )
    assert "ON CONFLICT (run_id) DO UPDATE SET run_time = excluded.run_time" in sql
    assert "runs.run_time IS DISTINCT FROM excluded.run_time" in sql
    assert "start_time" not in sql and "end_time" not in sql
    assert "RETURNING runs.run_id" in sql
