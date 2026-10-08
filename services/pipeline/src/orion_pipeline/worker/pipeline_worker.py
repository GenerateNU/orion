import logging
import time

from orion_pipeline.jobs.job_queue import JobQueue
from orion_pipeline.runner.pipeline_runner import PipelineRunner

logger = logging.getLogger(__name__)


class PipelineWorker:
    """Claims queued jobs one at a time and runs them. Plain sync Python: no async here."""

    def __init__(
        self, queue: JobQueue, runner: PipelineRunner, poll_seconds: float = 2
    ):
        self.queue = queue
        self.runner = runner
        self.poll_seconds = poll_seconds

    def run_forever(self) -> None:
        # TODO: also poll Penelope for finished run_ids and enqueue them (change-driven).
        while True:
            job = self.queue.claim_next()
            if job is None:
                time.sleep(self.poll_seconds)
                continue
            try:
                self.runner.run(job.run_id)
                self.queue.finish(job.id)
            except Exception as exc:
                logger.exception("job %s failed", job.id)
                self.queue.finish(job.id, error=str(exc))
