"""Route tests swap the service for a fake via FastAPI's dependency_overrides,
so they don't need a database."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from orion_backend.core.exceptions import NotFoundError
from orion_backend.main import app
from orion_backend.routes.run_route import get_run_service
from orion_backend.schemas.run_schema import RunResponse

RUN = RunResponse(run_id="run-1", created_at=datetime(2026, 1, 1, tzinfo=UTC))


class FakeRunService:
    async def list_runs(self):
        return [RUN]

    async def get_run(self, run_id):
        if run_id != RUN.run_id:
            raise NotFoundError("Run", run_id)
        return RUN


app.dependency_overrides[get_run_service] = FakeRunService
client = TestClient(app)


def test_list_runs():
    response = client.get("/api/v1/runs")
    assert response.status_code == 200
    assert response.json()[0]["run_id"] == "run-1"


def test_missing_run_is_404_with_error_shape():
    response = client.get("/api/v1/runs/nope")
    assert response.status_code == 404
    assert response.json()["resource_id"] == "nope"
