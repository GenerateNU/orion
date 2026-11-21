import logging

from orion_core.db.engines import make_sync_engine
from orion_core.settings import Settings
from orion_pipeline import steps  # noqa: F401  (importing registers every step)
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.clients.penelope_client import PenelopeClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.step_registry import ordered_steps

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Runs every registered step for one run_id, in dependency order."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.oriondb = OrionDBClient(
            make_sync_engine(settings.orion_database_url),
            page_size=settings.pipeline_page_size,
        )
        self.penelope = (
            PenelopeClient(
                make_sync_engine(settings.penelope_database_url, read_only=True),
                page_size=settings.pipeline_page_size,
            )
            if settings.penelope_database_url
            else None
        )

    # Runs each step in order
    def run_all(self, run_id: str) -> None:
        ctx = self._context(run_id)
        for step_cls in ordered_steps():
            self._run(step_cls, ctx)

    # Runs start_step and every step after it, in order. Later steps use the
    # earlier ones' output, so re-running a step means re-running what follows it.
    def run_from(self, run_id: str, start_step: str) -> None:
        order = ordered_steps()
        start = [s.name for s in order].index(start_step)
        ctx = self._context(run_id)
        for step_cls in order[start:]:
            self._run(step_cls, ctx)

    def _context(self, run_id: str) -> RunContext:
        return RunContext(
            run_id=run_id,
            gps_time_offset_s=self.settings.gps_time_offset_s,
            lap_hitbox_radius_m=self.settings.lap_hitbox_radius_m,
            lap_min_revisit_time_s=self.settings.lap_min_revisit_time_s,
            lap_min_revisit_distance_m=self.settings.lap_min_revisit_distance_m,
            lap_gate_search_sample_every=self.settings.lap_gate_search_sample_every,
            lap_gate_half_width_m=self.settings.lap_gate_half_width_m,
            lap_min_lap_time_s=self.settings.lap_min_lap_time_s,
        )

    def _run(self, step_cls: type[PipelineStep], ctx: RunContext) -> None:
        # TODO: Switch ownership of DB to be in the step implementation directly.
        reader = self.penelope if step_cls.reads_from == "penelope" else self.oriondb
        if reader is None:
            raise RuntimeError(
                f"{step_cls.name} reads from Penelope, "
                "but PENELOPE_DATABASE_URL is not set"
            )
        logger.info("run %s: %s", ctx.run_id, step_cls.name)
        step_cls(reader=reader, writer=self.oriondb).run(ctx)
