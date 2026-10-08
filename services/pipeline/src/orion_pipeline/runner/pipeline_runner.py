import logging

from orion_core.db.engines import make_sync_engine
from orion_core.settings import Settings
from orion_pipeline import steps  # noqa: F401  (importing registers every step)
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.clients.penelope_client import PenelopeClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.step_registry import ordered_steps

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Runs every registered step for one run_id, in dependency order."""

    def __init__(self, settings: Settings):
        self.oriondb = OrionDBClient(make_sync_engine(settings.orion_database_url))
        self.penelope = (
            PenelopeClient(
                make_sync_engine(settings.penelope_database_url, read_only=True)
            )
            if settings.penelope_database_url
            else None
        )

    def run(self, run_id: str) -> None:
        ctx = RunContext(run_id=run_id)
        for step_cls in ordered_steps():
            reader = (
                self.penelope if step_cls.reads_from == "penelope" else self.oriondb
            )
            logger.info("run %s: %s", run_id, step_cls.name)
            step_cls(reader=reader, writer=self.oriondb).run(ctx)
