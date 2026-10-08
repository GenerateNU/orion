"""Entry point: `orion-pipeline api | worker | run <run_id>`."""

import argparse
import logging

import uvicorn

from orion_core.db.engines import make_sync_engine
from orion_core.settings import get_settings
from orion_pipeline.jobs.job_queue import JobQueue
from orion_pipeline.runner.pipeline_runner import PipelineRunner
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
    else:
        PipelineRunner(settings).run(args.run_id)


if __name__ == "__main__":
    main()
