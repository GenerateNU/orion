import pytest

from orion_core.models import PipelineRun
from orion_pipeline.worker.pipeline_worker import PipelineWorker


class StopWorker(Exception):
    """Raised by FakeQueue to end run_forever's loop."""


class FakeQueue:
    """Hands out one job, then stops the worker."""

    def __init__(self, job: PipelineRun):
        self.jobs = [job]
        self.finished: list[int] = []

    def claim_next(self) -> PipelineRun:
        if not self.jobs:
            raise StopWorker
        return self.jobs.pop()

    def finish(self, job_id: int, error: str | None = None) -> None:
        self.finished.append(job_id)


class FakeRunner:
    """Records which runner method the worker called."""

    def __init__(self):
        self.calls: list[tuple[str, ...]] = []

    def run_all(self, run_id: str) -> None:
        self.calls.append(("run_all", run_id))

    def run_from(self, run_id: str, start_step: str) -> None:
        self.calls.append(("run_from", run_id, start_step))


def run_one_job(step: str | None) -> list[tuple[str, ...]]:
    """Have the worker process one job, then return the runner calls it made."""
    queue = FakeQueue(PipelineRun(id=1, run_id="run-1", step=step))
    runner = FakeRunner()
    with pytest.raises(StopWorker):
        PipelineWorker(queue, runner).run_forever()  # type: ignore[arg-type]
    assert queue.finished == [1]
    return runner.calls


def test_job_with_a_step_runs_from_that_step():
    assert run_one_job("state_step") == [("run_from", "run-1", "state_step")]


def test_job_without_a_step_runs_the_whole_pipeline():
    assert run_one_job(None) == [("run_all", "run-1")]
