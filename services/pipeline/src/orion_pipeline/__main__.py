"""Entry point: `orion-pipeline api | worker | run <run_id> | sync`."""

import argparse
import logging

import uvicorn

from orion_core.db.engines import make_sync_engine
from orion_core.settings import get_settings
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.clients.penelope_client import PenelopeClient
from orion_pipeline.jobs.job_queue import JobQueue
from orion_pipeline.runner.pipeline_runner import PipelineRunner
from orion_pipeline.sync.penelope_sync import sync
from orion_pipeline.worker.pipeline_worker import PipelineWorker


def main() -> None:
    parser = argparse.ArgumentParser(prog="orion-pipeline")
    commands = parser.add_subparsers(dest="command", required=True)
    api = commands.add_parser("api", help="Serve the trigger/status API")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8200)
    api.add_argument("--reload", action="store_true")
    commands.add_parser("worker", help="Process queued jobs forever")
    run = commands.add_parser("run", help="Run the pipeline for one run_id, right now")
    run.add_argument("run_id")
    commands.add_parser(
        "sync", help="Copy new Penelope data into OrionDB's penelope schema"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if args.command == "api":
        uvicorn.run(
            "orion_pipeline.api.pipeline_api:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    elif args.command == "worker":
        queue = JobQueue(make_sync_engine(settings.orion_database_url))
        PipelineWorker(queue, PipelineRunner(settings)).run_forever()
    elif args.command == "sync":
        if not settings.penelope_database_url:
            raise SystemExit("PENELOPE_DATABASE_URL is not set")
        penelope = PenelopeClient(
            make_sync_engine(settings.penelope_database_url, read_only=True),
            page_size=settings.pipeline_page_size,
        )
        oriondb = OrionDBClient(
            make_sync_engine(settings.orion_database_url),
            page_size=settings.pipeline_page_size,
        )
        sync(penelope, oriondb)
    else:
        PipelineRunner(settings).run_all(args.run_id)


if __name__ == "__main__":
    main()
