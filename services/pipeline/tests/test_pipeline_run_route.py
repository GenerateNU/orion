from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from orion_core.models import PipelineRun
from orion_pipeline.api.routes import pipeline_run_route


class FakeQueue:
    """Records enqueue calls and returns a queued job, without a database."""

    def __init__(self):
        self.enqueued: list[tuple[str, str | None]] = []

    def enqueue(self, run_id: str, step: str | None = None) -> PipelineRun:
        self.enqueued.append((run_id, step))
        return PipelineRun(
            id=1,
            run_id=run_id,
            step=step,
            status="queued",
            error=None,
            queued_at=datetime(2026, 11, 15, tzinfo=UTC),
        )


def make_client() -> tuple[TestClient, FakeQueue]:
    """The runs router with a fake job queue (no database, no lifespan)."""
    app = FastAPI()
    app.include_router(pipeline_run_route.router)
    queue = FakeQueue()
    app.state.queue = queue
    return TestClient(app), queue


def test_queues_a_job_from_a_step():
    client, queue = make_client()
    response = client.post("/runs", json={"run_id": "run-1", "step": "clean_step"})
    assert response.status_code == 202
    assert response.json()["step"] == "clean_step"
    assert queue.enqueued == [("run-1", "clean_step")]


def test_rejects_an_unknown_step():
    client, queue = make_client()
    response = client.post("/runs", json={"run_id": "run-1", "step": "cleaning"})
    assert response.status_code == 400
    assert "cleaning" in response.json()["detail"]
    assert queue.enqueued == []
