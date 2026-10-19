# orion: developer guide

Technical documentation for working on Orion. For what the application is and
does, see [README.md](README.md).

Orion is a uv workspace monorepo with one shared Python package, two Python
services, and a frontend, all run locally with Docker Compose.

```
packages/orion_core/   shared Python: settings, DB models + migrations, queries
services/backend/      main API (orion_backend)
services/pipeline/     pipeline API + worker (orion_pipeline)
frontend/              React app
docker/                python.Dockerfile: one image for every Python service
docs/                  design notes (ARCHITECTURE.md, …)
pyproject.toml         uv workspace root and shared ruff/mypy/pytest config
docker-compose.yml     the local stack
Makefile               shortcuts (`make help`)
```

## Running with Docker

```bash
cp .env.example .env        # fill in PENELOPE_DATABASE_URL (see "Configuration")
docker compose up --build
```

Then seed the sensor catalog once. The pipeline can't clean anything without it:

```bash
docker compose exec orion-backend python -m orion_core.db.scripts.seed_sensors
```

| Service                 | URL                          | What it is                               |
| ----------------------- | ---------------------------- | ---------------------------------------- |
| `frontend`              | http://localhost:5173        | React + Vite dev server                  |
| `orion-backend`         | http://localhost:8100/docs   | Main API (Swagger UI)                    |
| `orion-pipeline-api`    | http://localhost:8200/docs   | Pipeline trigger/status API              |
| `orion-pipeline-worker` | (none)                       | Runs queued pipeline jobs                |
| `orion-db`              | `localhost:5434`             | Local OrionDB (Postgres 16)              |
| `orion-migrate`         | (one-shot)                   | `alembic upgrade head`, then exits       |

`packages/`, `services/` and `frontend/` are bind-mounted into the containers, so
changes hot-reload. The worker doesn't reload: run `docker compose restart orion-pipeline-worker` after changing step code.

Run `make help` for the full list of shortcuts (`make up`, `make logs`, `make migrate`, `make quality`, …).

## Architecture

```
                 ┌──────────────┐   /api/*  (Vite proxy)
   browser ────► │   frontend   │ ─────────────────────────┐
                 └──────────────┘                          ▼
                                                 ┌───────────────────┐
                                                 │   orion-backend   │  async FastAPI
                                                 └───────────────────┘
                     reads/writes  │   read-only │       │ HTTP: trigger / status
                                   ▼             ▼       ▼
                           ┌──────────┐  ┌──────────┐  ┌──────────────────────┐
                           │ OrionDB  │  │ Penelope │  │ orion-pipeline-api   │
                           └──────────┘  └──────────┘  └──────────────────────┘
                              ▲  ▲            │               │ INSERT queued job
              pipeline_runs   │  │ writes     │ reads         ▼
              (job queue) ────┘  │ outputs    │        pipeline_runs table
                                 │            ▼               │ claim (SKIP LOCKED)
                           ┌─────────────────────────────┐    │
                           │   orion-pipeline-worker     │ ◄──┘
                           │   steps: clean → … (DAG)    │  sync, pandas
                           └─────────────────────────────┘
```

### Databases

- **Penelope** is NER's Postgres database of every published sensor reading
  (`run`, `data`, `data_type` tables). Orion only ever **reads** it, and that is
  enforced three ways: a read-only role, `default_transaction_read_only=on` on
  every engine, and clients with no write methods. `PENELOPE_DATABASE_URL` points
  at either the real Penelope (needs the NER VPN) or `penelope2`, a Neon copy with
  the same schema. No code changes are needed to switch.
- **OrionDB** is our database and holds everything we derive. Its schema is owned by
  `orion_core` and migrated with Alembic.

| OrionDB table         | Contents                                                              |
| --------------------- | --------------------------------------------------------------------- |
| `runs`                | One row per Penelope run (`run_id`), the unit of pipeline work        |
| `pipeline_runs`       | Pipeline jobs: the job queue *and* their history (status, error, timestamps) |
| `sensors`             | Our clean sensor names and units                                      |
| `sensor_sources`      | Maps each Penelope `raw_tag` (`dataTypeName`) to a sensor             |
| `cleaned_data`        | Output of the clean step: `run_id, time, sensor, values`              |
| `estimated_car_state` | Output of state estimation (step not implemented yet)                 |

Naming: **`run_id`** (a string) identifies a run everywhere. **`raw_tag`** is Penelope's
name for a sensor, and **`sensor`** is our cleaned name for it.

### `packages/orion_core`: shared code

Both services import this package. Neither service defines its own tables.

```
packages/orion_core/
├── alembic.ini, alembic/       THE only migrations
└── src/orion_core/
    ├── settings.py             Settings, read from env / .env (get_settings())
    ├── db/engines.py           make_async_engine / make_sync_engine (read_only=True for Penelope)
    ├── db/sensor_catalog.py    raw_tag → sensor + unit mapping (source of truth for seeding)
    ├── db/scripts/seed_sensors.py   upserts sensors + sensor_sources from the catalog
    ├── models/orion/           SQLAlchemy models, one per file, on Base.metadata
    ├── models/penelope/        Penelope tables on a SEPARATE MetaData, so Alembic never sees them
    ├── queries/                SELECT/INSERT builders shared by the async backend and the sync pipeline
    └── schemas/                Pydantic schemas shared by both services (pipeline jobs)
```

### `services/backend`: the API (`orion_backend`)

This is an async FastAPI app (SQLAlchemy async + asyncpg). All routes live under `/api/v1` and are
documented at `/docs`. Each entity has one file per layer:

```
routes/        HTTP only: params, response_model, status codes      *_route.py
services/      business rules, raises domain errors (NotFoundError…) *_service.py
repositories/  runs the shared query builders, returns models/None   *_repository.py
schemas/       Pydantic request/response models                      *_schema.py
core/          engines + session dependencies, exception → ErrorResponse mapping, OpenAPI conventions
```

`get_orion_db` commits once per request, so repositories never commit. Penelope
sessions never commit. If `PENELOPE_DATABASE_URL` is unset, routes that need
Penelope return 503, and the run list just omits Penelope's run times.

| Route                               | Source        |
| ----------------------------------- | ------------- |
| `GET /health`                       | none          |
| `GET /runs`, `GET/DELETE /runs/{run_id}` | OrionDB  |
| `GET /penelope/runs`                | Penelope, each run flagged `processed` |
| `GET /sensors`                      | Penelope      |
| `GET /runs/{run_id}/sensors/data`   | Penelope      |
| `GET /runs/{run_id}/state`          | OrionDB `estimated_car_state` |
| `POST/GET /pipeline/runs`, `GET /pipeline/runs/{id}` | forwarded to the pipeline API |

The backend **never runs pipeline code**. It reaches the pipeline over HTTP (`PIPELINE_API_URL`).

### `services/pipeline`: data processing (`orion_pipeline`)

All three entry points are in one CLI, `orion-pipeline`:

| Command                          | What it does                                                       |
| -------------------------------- | ------------------------------------------------------------------ |
| `orion-pipeline api`             | Thin async FastAPI app: enqueue a job, list/get jobs. Never runs pandas. |
| `orion-pipeline worker`          | Sync loop: claim the oldest queued job, run every step, mark it finished/failed |
| `orion-pipeline run <run_id>`    | Run the whole pipeline for one run in the foreground (debugging, backfills). `make pipeline-run RUN_ID=…` |

```
api/       trigger/status API (pipeline_api.py + routes/)
jobs/      JobQueue: the pipeline_runs table used as a queue (no Redis/Celery)
worker/    PipelineWorker: claim → run → finish
runner/    PipelineRunner: builds DB clients, runs steps in dependency order; RunContext
clients/   sync, DataFrame-speaking DB access (PenelopeClient read-only, OrionDBClient read/write)
steps/     PipelineStep base class, step registry (DAG), and one folder per step
```

How a job flows:

1. The frontend calls `POST /api/v1/pipeline/runs`, the backend forwards it to the pipeline API, and
   the pipeline API inserts a `queued` row into `pipeline_runs`. If the run
   already has a queued or running job, it returns 409 instead.
2. The worker claims the job with `SELECT … FOR UPDATE SKIP LOCKED` and marks it `running`.
3. `PipelineRunner` runs every registered step in topological order.
4. The job is marked `succeeded`, or `failed` with the error message. The frontend polls its status.

**Steps** subclass `PipelineStep` and are registered with `@register_step`. Each
step runs `prepare` (by default it deletes the run's old output, so re-runs are
idempotent), then `extract` → `transform` → `write` one page at a time
(`PIPELINE_PAGE_SIZE` rows), so a run never has to fit in memory. Steps never
hand DataFrames to each other. Each step writes its output table, and the next
step reads that table back, so any step can be re-run on its own.

| Step         | Reads                  | Writes                | Status          |
| ------------ | ---------------------- | --------------------- | --------------- |
| `clean_step` | Penelope `data`        | `cleaned_data`        | Done: maps `raw_tag` → sensor via `sensor_sources`, applies GPS time offset |
| state        | `cleaned_data`         | `estimated_car_state` | Not started     |
| laps         | `estimated_car_state`  | TBD                   | Not started     |

To add a step, create `steps/<name>_step/<name>_step.py`, set `name`, `depends_on`,
`reads_from`, `output_table` and `pagination_key`, decorate the class with
`@register_step`, and import it in `steps/__init__.py`.

### `frontend/`

React 19 + TypeScript on Vite, with TanStack Router (routes defined in code in
`src/router.tsx`), TanStack Query (server state), Zustand (UI state), axios, and
zod (every response is validated against a schema in `src/schemas/`, which mirrors
the backend's Pydantic schemas).

```
src/api/         axios client (baseURL /api/v1), query keys, query options
src/schemas/     zod schemas for every backend response
src/hooks/       one data hook per resource (useRuns, usePipelineRuns, …)
src/views/       route-level pages (RunsView)
src/features/    larger features with their own state (dashboard/)
src/components/  layout/, ui/, runs/, plus shared Loading/Empty/Error states
src/utils/       apiUrls (every backend path), formatting, time helpers
```

The browser only ever calls relative `/api/...` URLs, and Vite's dev server
proxies them to `API_PROXY_TARGET`. This means the backend needs no CORS
setup, and the same code works on the host (`:8100`) and in Docker
(`orion-backend:8000`).

## Configuration

All variables go in the repo-root `.env`, which is shared by every service and the frontend. See `.env.example`.

| Variable                 | Default                         | Purpose                                         |
| ------------------------ | ------------------------------- | ----------------------------------------------- |
| `ORION_DATABASE_URL`     | local `orion-db` container      | OrionDB. Set it to use Neon instead.            |
| `PENELOPE_DATABASE_URL`  | unset (Penelope features off)   | Real Penelope (VPN) or penelope2 (Neon)         |
| `PIPELINE_API_URL`       | `http://localhost:8200`         | Where the backend reaches the pipeline API (compose sets it) |
| `PIPELINE_PAGE_SIZE`     | `100000`                        | Max rows per page in each pipeline step         |
| `GPS_TIME_OFFSET_S`      | `3`                             | Seconds added to `gps_location` timestamps      |
| `API_PROXY_TARGET`       | `http://localhost:8100`         | Where Vite forwards `/api` (compose sets it)    |

## Development without Docker

Requires [uv](https://docs.astral.sh/uv/) (Python 3.13) and Node 22+.

```bash
make install                       # uv sync: every workspace package into .venv
docker compose up -d orion-db      # or point ORION_DATABASE_URL at any Postgres
# ORION_DATABASE_URL=postgresql://orion:orion@localhost:5434/orion in .env
make migrate
uv run uvicorn orion_backend.main:app --port 8100 --reload
uv run orion-pipeline api --reload  # :8200
uv run orion-pipeline worker
cd frontend && npm install && npm run dev
```

### Migrations

Models live in `packages/orion_core/src/orion_core/models/orion/`. A new model
must be imported in `models/orion/__init__.py`, or Alembic won't see it.

```bash
make migration    # autogenerate from model changes (prompts for a name)
make migrate      # apply
```

### Code quality and CI

| Check | Locally | CI (`.github/workflows/`) |
| ----- | ------- | ------------------------- |
| ruff lint + format, pydoclint (Google-style docstrings) | `make lint`, `make format-check` | `BackendCI.yml` → `lint-services` |
| mypy (strict) | `make typecheck` | `BackendCI.yml` → `typecheck-services` |
| pytest (`services/*/tests`) | `make test` | not yet run in CI |
| ESLint, `tsc` + Vite build | `npm run lint`, `npm run build` | `FrontendCI.yml` → `lint-and-build` |

`make quality` runs all four Python checks, and `make format` auto-fixes what it
can. Backend CI runs on changes to `packages/`, `services/`, the root
`pyproject.toml`, `uv.lock` or `docker-compose.yml`. Frontend CI runs on changes
to `frontend/`.

There are no service tests yet, so `make test` (and therefore `make quality`)
fails ("no tests ran", exit code 5). When you add the first test under
`services/<name>/tests/`, add a pytest job to `BackendCI.yml` too.
