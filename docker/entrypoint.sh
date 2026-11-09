#!/usr/bin/env bash
# Runs migrations, then the backend, pipeline API and pipeline worker in one container.
# If any of the three exits, the others are stopped and the container exits with its status.
set -uo pipefail

alembic -c packages/orion_core/alembic.ini upgrade head || exit 1

orion-pipeline api --host 127.0.0.1 --port 8200 &
pipeline_api=$!
orion-pipeline worker &
worker=$!
uvicorn orion_backend.main:app --host 0.0.0.0 --port 8000 &
backend=$!

shutdown() {
  kill -INT "$worker" 2>/dev/null
  kill -TERM "$pipeline_api" "$backend" 2>/dev/null
  wait
}
trap 'shutdown; exit 0' TERM INT

wait -n
status=$?
echo "orion: a process exited with status $status; stopping the rest" >&2
shutdown
exit "$status"
