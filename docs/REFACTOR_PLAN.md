# Orion Refactor Plan: Backend + Pipeline Split

Status: **Skeleton implemented; target design below is for the follow-up tickets**. Reference architecture: `via-wms` (backend layering, async SQLAlchemy, Alembic, exception handling), improved where via-wms is weak (OpenAPI docs, Alembic config, naming conventions).

Frontend changes are **out of scope** for this round.

---

## 1. Decisions

| # | Decision | Why |
|---|---|---|
| D1 | **Two services**: `backend` (traditional FastAPI) and `pipeline` (data processing). | Different workloads: the backend answers many small requests, the pipeline does heavy CPU work on one run at a time. |
| D2 | **Backend is async** (SQLAlchemy async + asyncpg), following via-wms. | Web requests mostly *wait* on the DB; async lets one process serve many requests at once. |
| D3 | **Pipeline step code is sync** (SQLAlchemy sync + psycopg3, pandas, `COPY`). | Pipeline work is CPU-bound (pandas, Kalman math), so async gains nothing and adds `run_sync` boilerplate. Steps read like notebook code. |
| D4 | **The pipeline API never runs pandas.** A thin async FastAPI app accepts triggers and streams status; a separate **worker process** runs steps. | Running sync CPU work inside `async def` endpoints would freeze the API. Separate processes avoid that. |
| D5 | **Steps communicate through OrionDB tables**, never in-memory hand-off. | Any step can be re-run alone (e.g. re-tune the Kalman filter without re-ingesting). Changes #17's "return a DataFrame" requirement to "write `cleaned_data`". |
| D6 | **Unit of work = one `run_id`.** Steps form a DAG ordered by `graphlib.TopologicalSorter`. | Agreed scope. Keep the interfaces built around a `RunContext` so a future "time range" context can replace it. |
| D7 | **Job queue = our own `pipeline_runs` table** in OrionDB. Worker claims jobs with `SELECT … FOR UPDATE SKIP LOCKED`. One worker, one run at a time. | No Redis/Celery. Survives restarts. The backend can read status straight from the DB. |
| D8 | **Concurrency safety**: partial unique index (only one queued or running job per `run_id`), plus idempotent writes (delete-then-`COPY` per `run_id` in one transaction). | The same run_id triggered twice (by the poller and by HTTP) can't run twice or duplicate rows. |
| D9 | **uv workspace monorepo** with a shared `orion_core` package that owns models, settings, table definitions, and the **single Alembic setup**. | One source of truth for schema. Both services import it; neither defines its own tables. |
| D10 | **Penelope vs penelope2 is a config switch**: `PENELOPE_DATABASE_URL` points at either the real Penelope (VPN) or the penelope2 Neon database. Same table definitions, same client. | penelope2 is a separate Neon DB with identical schema, so no code changes are needed to swap. |
| D11 | **Penelope is read-only at three layers**: a read-only Postgres role, `default_transaction_read_only=on` on the engine, and clients that expose no write methods. | Defense in depth. We can never accidentally write to NER's DB. |
| D12 | **Penelope tables live in a separate `MetaData` that Alembic never sees.** | Autogenerate must never emit DDL against Penelope. |
| D13 | Standardize names: **`run_id: str`** everywhere (replace `race_id: int` and `session_id`). **`raw_tag`** = Penelope `dataTypeName`; **`signal`** = our clean name. | Removes the current naming drift. |
| D14 | Local / docker-compose only for now. | No hosted deploy yet; keep everything container-friendly. |

---

## 2. Layout (skeleton is in place)

The skeleton on branch `refactor/backend-pipeline-split` has every layer wired
end to end, but only **example** slices and steps. Real logic lands in the
follow-up tickets (#17, #18, #41, …), and each `TODO` in the code points at one.
The existing `backend/` and `frontend/` are untouched.

```
orion/
├── pyproject.toml                  # uv workspace root (`uv sync` installs everything)
├── uv.lock                         # single lockfile
├── Makefile                        # `make help` (via-wms style, Git Bash on Windows)
├── docker-compose.yml              # orion-db, orion-migrate, orion-backend, orion-pipeline-api/-worker (+ legacy)
├── docker/python.Dockerfile        # one image for every Python service
│
├── packages/orion_core/            # shared by both services
│   ├── alembic.ini + alembic/      # THE only migrations (`make migration`, `make migrate`)
│   └── src/orion_core/
│       ├── settings.py             # Settings: ORION_DATABASE_URL, PENELOPE_DATABASE_URL, …
│       ├── db/engines.py           # make_async_engine / make_sync_engine (read_only=True for Penelope)
│       ├── db/orion/base.py        # Base (DeclarativeBase + constraint naming convention)
│       ├── db/orion/models/        # run_model.py, pipeline_run_model.py (one class per file)
│       ├── db/penelope/penelope_tables.py   # separate MetaData → Alembic never sees it
│       ├── queries/penelope_queries.py      # SELECT builders shared by async + sync code
│       └── schemas/pipeline_run_schema.py   # API schemas both services use
│
└── services/
    ├── backend/src/orion_backend/  # async FastAPI, via-wms layering
    │   ├── main.py, api.py         # app + /api/v1 router
    │   ├── core/                   # database.py, exceptions.py, exception_handlers.py, openapi.py
    │   ├── routes/                 # run_route.py (OrionDB slice), reading_route.py (Penelope slice),
    │   │                           # pipeline_route.py (trigger), health_route.py
    │   ├── services/               # run_service.py, reading_service.py, pipeline_service.py
    │   ├── repositories/           # run_repository.py, reading_repository.py
    │   └── schemas/                # run_schema.py, reading_schema.py, error_schema.py
    │
    └── pipeline/src/orion_pipeline/   # sync; `orion-pipeline api | worker | run <run_id>`
        ├── api/                    # pipeline_api.py + routes/pipeline_run_route.py (queue + status)
        ├── jobs/job_queue.py       # pipeline_runs table as a queue (FOR UPDATE SKIP LOCKED)
        ├── worker/pipeline_worker.py   # claim → run → finish loop
        ├── runner/                 # pipeline_runner.py (DAG order), run_context.py
        ├── clients/                # base_client.py, penelope_client.py (read-only), oriondb_client.py
        └── steps/                  # base_step.py, step_registry.py,
                                    # example_ingest_step.py → example_estimate_step.py
```

**Request flow:** `POST /api/v1/pipeline/runs` on the backend → pipeline API inserts a
`queued` row in `pipeline_runs` → the worker claims it → `PipelineRunner` runs every
registered step in dependency order → the row becomes `succeeded` / `failed`.

**Adding a real step:** create `steps/<name>_step.py` with a `@register_step` class
(`name`, `depends_on`, `reads_from`, `output_table`, `extract`, `transform`), import it
in `steps/__init__.py`, add its output model to `orion_core` and run `make migration`.
Then delete the example steps.

**Why `queries/` lives in core but execution doesn't:** the backend needs **async** access to Penelope (signal explorer) and the pipeline needs **sync** access (ingest). Both import the same `select()` builders and table definitions from `orion_core`. The backend executes them in async repositories; the pipeline executes them with `pd.read_sql` in sync clients. Query logic isn't duplicated, and neither service is forced into the other's concurrency model.

---

## 3. Shared core (`orion_core`)

### Settings
One `pydantic_settings.BaseSettings` using `model_config = SettingsConfigDict(env_file=".env")`:

```
ORION_DATABASE_URL          # Neon, pooled host (backend + pipeline)
ORION_DATABASE_URL_DIRECT   # Neon, direct host (Alembic + long pipeline transactions)
PENELOPE_DATABASE_URL       # real Penelope (VPN) OR penelope2 (Neon): the swap (D10)
PIPELINE_API_URL            # backend → pipeline
PIPELINE_POLL_INTERVAL_S
GPS_LAG_S                   # from #17
```
Engines build the driver suffix themselves (`+asyncpg` for backend, `+psycopg` for pipeline/Alembic), so one URL per DB.

### DB base (improving on via-wms)
- `class Base(DeclarativeBase)` with `MetaData(naming_convention={...})` (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`), so constraints have stable, diffable names.
- `TimestampMixin` (`created_at`, `updated_at`, server defaults).
- `Mapped[...]` / `mapped_column` everywhere; relationships `lazy="raise"` (via-wms convention: forces explicit `selectinload`).
- `models/__init__.py` imports every model so Alembic sees them.

### Alembic (single source, D9)
- Lives in `packages/orion_core/alembic/`; `target_metadata = Base.metadata` (OrionDB only).
- `include_object` filter as a second guard so Penelope tables can never appear in autogenerate.
- `compare_type=True`, `compare_server_default=True`.
- `file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s`: date-prefixed files sort chronologically (via-wms has ~2 merge-head migrations; dated names make parallel heads easier to spot).
- `post_write_hooks`: ruff format on generated files.
- Runs over the **direct** (non-pooler) Neon URL with sync psycopg.
- Run via `make migrate` / `make migration name="…"`, and a one-shot `migrate` compose service that `backend` and `pipeline-*` depend on (`condition: service_completed_successfully`), the local equivalent of via-wms's migrate-before-deploy task.
- Signals catalog seeded with `make seed` (idempotent upsert from `signals_catalog.py`).

### Initial OrionDB tables (first migration)

| Table | Purpose |
|---|---|
| `runs` | One row per Penelope `run_id` we know about: time bounds, discovered_at, latest pipeline status. |
| `signals` | Clean signal catalog: `signal` (PK), display_name, description, unit. |
| `signal_sources` | `raw_tag` + `value_index` → `signal`. Maps Penelope's `values[]` array positions to clean signals (e.g. `TPU/GPS/Location` [0]→`gps_lat`, [1]→`gps_lon`). Merges #17's `sensors`/`sensor_sources` idea with #40's `signals`. |
| `cleaned_data` | Long format `(run_id, time, signal, value)`, PK `(run_id, signal, time)`. Output of ingest_clean. |
| `vehicle_state` | Wide 100 Hz state trace per run (CTRA states + lat/lon). Output of state_estimation. |
| `laps` | `(run_id, lap_number, start_time, end_time, …)`. Output of lap_detection. |
| `lap_metrics` | Output of metrics. |
| `pipeline_runs` | Job queue + history: `id, run_id, steps[], status (queued/running/succeeded/failed/cancelled), trigger (poller/api/cli), current_step, error, queued_at, started_at, finished_at`. Partial unique index on `run_id WHERE status IN ('queued','running')` (D8). |
| `pipeline_step_runs` | Per-step record: `pipeline_run_id, step, status, rows_in, rows_out, started_at, finished_at, error`. Drives progress streaming. |

Large time-series tables (`cleaned_data`, `vehicle_state`) are candidates for partitioning by `run_id` later (as `ARCHITECTURE.md` suggests). We won't do it in the first pass.

---

## 4. Backend service

Follows via-wms closely: **routes → services → repositories**, one file per entity per layer (`run_route.py`, `run_service.py`, `run_repository.py`, `run_schema.py`).

### DB access
- Two async engines created in `lifespan` and disposed on shutdown (via-wms only prints in its lifespan):
  - `orion_engine`: read/write.
  - `penelope_engine`: read-only (`connect_args={"server_settings": {"default_transaction_read_only": "on"}}`).
- Dependencies in `core/deps.py`:
  - `get_orion_db()`: via-wms's commit-once-per-request pattern (yield session → commit → rollback on error). Repositories only `flush()`.
  - `get_penelope_db()`: yields a session, never commits.
- Neon pooler + asyncpg: set `statement_cache_size=0` / `prepared_statement_cache_size=0` (PgBouncer transaction mode).

### Self-documenting API (where we go beyond via-wms)
- All routes under `/api/v1`.
- `FastAPI(title, version=<package version>, description=<markdown>, openapi_tags=[{name, description}…])`.
- `generate_unique_id_function=lambda r: f"{r.tags[0]}-{r.name}"`: clean, stable `operationId`s (ready for a generated frontend client later).
- Every route: `response_model`, `status_code`, `summary=`, docstring as the long description, and `responses={404: {"model": ErrorResponse}, …}`.
- Every schema field: `Field(description=..., examples=[...])`. Query params use `Annotated[..., Query(description=...)]`.
- Domain exceptions (`NotFoundError`, `ConflictError`, `ValidationError`, `UpstreamError`) mapped by `register_exception_handlers` (specific first, catch-all last, as in via-wms) to one documented `ErrorResponse` shape.
- Structured logging via `logging` with a JSON or rich formatter (via-wms uses `print`).

### Initial endpoints

| Tag | Route | Source | Notes |
|---|---|---|---|
| runs | `GET /runs` | OrionDB | Replaces `/api/races` (#18). |
| runs | `GET /runs/{run_id}` | OrionDB | |
| laps | `GET /runs/{run_id}/laps`, `/laps/{n}` | OrionDB | |
| positions | `GET /runs/{run_id}/positions?lap=&start=&end=` | OrionDB `vehicle_state` | Track shape / map. |
| signals | `GET /signals` | OrionDB catalog | What the user can pick. |
| signals | `GET /runs/{run_id}/signals/data?signals=a,b&start=&end=&x=time\|distance&max_points=` | **Penelope** + OrionDB | The "Grafana-style" explorer (see below). |
| pipeline | `POST /pipeline/runs` | → pipeline API | Swagger-only trigger. Body: `run_id`, optional `steps`. |
| pipeline | `GET /pipeline/runs/{id}` | OrionDB `pipeline_runs` | |
| pipeline | `GET /pipeline/runs/{id}/events` | → pipeline SSE | Relays the pipeline's Server-Sent Events stream. |
| health | `GET /health` | | Checks both DBs. |

### Signal explorer endpoint (the main Penelope use case)
1. Resolve requested clean `signals` → `(raw_tag, value_index)` via `signal_sources`.
2. Query Penelope (`penelope_repository`, async, read-only) for those raw tags in `[start, end]`.
3. If `x=distance` (or position), load the run's `vehicle_state` from OrionDB.
4. CPU work runs in `run_in_threadpool` (D4 applies to the backend too):
   - explode `values[]`
   - `pd.merge_asof` onto position by time
   - **downsample to `max_points`** (bucket min/max or LTTB) so the browser isn't sent 1M points.
5. Return columnar JSON (`{x: [...], series: {signal: [...]}}`).

Note: against the real Penelope this needs the VPN; against penelope2 it doesn't.

---

## 5. Pipeline service

### Process model (D4)
One Docker image, **two compose services**:

- `pipeline-api`: `python -m pipeline api` (uvicorn). Async. Only reads and writes `pipeline_runs` / `pipeline_step_runs`. Never imports pandas-heavy step code at request time.
- `pipeline-worker`: `python -m pipeline worker`. Sync. Loop:
  1. **Poll** Penelope every `PIPELINE_POLL_INTERVAL_S` for `run_id`s not yet in `runs` that are *complete* (see open question Q1) → insert `runs` row + queued `pipeline_runs` row (`trigger=poller`).
  2. **Claim** the oldest queued job: `UPDATE … SET status='running' WHERE id = (SELECT id … WHERE status='queued' ORDER BY queued_at FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *`.
  3. **Run** it through the runner. On crash/restart, any `running` job whose worker is gone is reset to `queued` at worker startup.
- Dev escape hatch: `python -m pipeline run --run-id X [--step state_estimation]` runs synchronously in the terminal (backfills, debugging), using the same runner.

### Trigger + streaming flow
```
Swagger → backend POST /api/v1/pipeline/runs
        → pipeline-api POST /runs           (insert queued row; 409 if one is already active, via D8)
        ← 202 {pipeline_run_id}
worker  → claims row, runs steps, writes pipeline_step_runs + progress
Swagger → backend GET /api/v1/pipeline/runs/{id}/events
        → pipeline-api GET /runs/{id}/events (SSE: polls pipeline_step_runs or LISTEN/NOTIFY)
```

### Clients
```python
class BaseClient(ABC):
    """Sync, DataFrame-returning DB access. Owns an Engine; steps never see sessions."""
    def __init__(self, engine: Engine): ...
    def read_frame(self, stmt: Select, chunksize: int | None = None) -> pd.DataFrame | Iterator[pd.DataFrame]: ...

class PenelopeClient(BaseClient):        # read-only; no write methods exist
    def fetch_readings(self, run_id, raw_tags, start=None, end=None, chunksize=...) -> Iterator[pd.DataFrame]: ...
    def list_run_ids(self, since=None) -> pd.DataFrame: ...

class OrionDBClient(BaseClient):
    def fetch_cleaned(self, run_id, signals=None) -> pd.DataFrame: ...
    def replace_for_run(self, table, run_id, frames: Iterable[pd.DataFrame]) -> int:
        """One transaction: DELETE WHERE run_id=… then COPY each chunk. Idempotent (D8)."""
```
- Penelope engine is created lazily with read-only options (fixes the current eager reflection in `__init__`).
- Bulk writes use psycopg3 `cursor.copy()`, which is much faster than `to_sql` or per-row inserts.
- No per-row Pydantic validation. DataFrame validation is done with **pandera** at step boundaries (replaces `models/frames.py`).

### Step abstraction
Your proposed design, with one change: **the writer is injected too** (defaulting to OrionDB in production), so tests can pass a fake writer.

```python
class PipelineStep(ABC):
    name: ClassVar[str]
    depends_on: ClassVar[tuple[str, ...]] = ()
    output_table: ClassVar[str]
    output_schema: ClassVar[type[pa.DataFrameModel]]

    def __init__(self, reader: BaseClient, writer: OrionDBClient): ...

    @abstractmethod
    def extract(self, ctx: RunContext) -> pd.DataFrame | Iterator[pd.DataFrame]: ...

    @abstractmethod
    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """PURE: no I/O. This is what most tests target."""

    def load(self, ctx: RunContext, frames: Iterable[pd.DataFrame]) -> int:
        return self.writer.replace_for_run(self.output_table, ctx.run_id, frames)

    def run(self, ctx: RunContext) -> StepResult:
        """Template method: extract → transform (per chunk) → validate(output_schema) → load,
        reporting rows_in/rows_out/progress to ctx.reporter."""
```
- Registration: a `@register_step` decorator puts each step in a registry. The runner builds `TopologicalSorter({s.name: s.depends_on})` and, given a requested step, also runs its downstream dependents (re-running `state_estimation` re-runs `lap_detection` and `metrics`).
- **Chunking is per step:**
  - `ingest_clean` streams Penelope in time windows (about 60 s ≈ 170k raw rows) so a full run is never in memory (#17 requirement).
  - `state_estimation` needs the **whole run**, because the RTS smoother runs backward over it. After filtering, about 1M long rows pivot to a manageable wide frame, so this step returns a single DataFrame from `extract`.
- `RunContext` carries `run_id`, optional `start/end`, settings (e.g. `GPS_LAG_S`, sensor noise constants for #41), and the progress reporter. A future "time range across runs" mode swaps the context, not the step interface.

### Initial DAG
```
ingest_clean (reader=Penelope)  →  state_estimation (reader=OrionDB)  →  lap_detection  →  metrics
     #17                                #41
```

---

## 6. Testing & tooling
- **Step `transform` tests**: pure pandas fixtures, no DB (`assert_frame_equal`, pandera). Fast; most coverage lives here.
- **Repository/client tests**: compose Postgres built by `alembic upgrade head` (not `create_all`), rollback-per-test session fixture (via-wms pattern).
- **Backend route tests**: `httpx.AsyncClient` against the app for a few contract checks (via-wms has none; the current repo's broken `get_lap` would have been caught).
- `pytest-asyncio` with `asyncio_mode=auto` for the backend.
- Ruff (`E,W,F,I,B,C4,UP`) + `ruff format`; pre-commit optional.
- CI: lint + tests per service with `uv sync --package <svc>` (catches undeclared imports that a shared workspace venv would hide). Coverage is measured over each service's `src/` and `orion_core`.
- Makefile targets: `help up down logs migrate migration seed test lint fmt pipeline-run`.
- Python **3.13** across the workspace.

---

## 7. Execution order (PRs)
Refactor first, then in-flight tickets (#17, #18, #41) are ported onto the skeleton.

1. **Workspace skeleton**
   - Root workspace `pyproject.toml`.
   - Move `backend/` → `services/backend/`; create `packages/orion_core`, `services/pipeline`.
   - Settings, Makefile, compose (`db`, `migrate`, `backend`, `pipeline-api`, `pipeline-worker`).
   - Remove `requirements.txt`, committed `coverage.xml`, `temp_orion/`.
2. **Core DB + Alembic**: Base/naming convention, OrionDB models (§3), Penelope tables, initial migration, signals catalog seed (with `value_index` mappings).
3. **Backend rebuild**: deps, exceptions, OpenAPI conventions, `runs`/`laps`/`positions`/`signals` endpoints (**absorbs #18**), health.
4. **Pipeline skeleton**: clients, `PipelineStep`, registry/runner, `pipeline_runs` claim loop, CLI, pipeline API + SSE, backend trigger/relay endpoints. Ship with a trivial `noop` step to prove the loop end to end.
5. **Port steps**: `ingest_clean` (**#17**, rewritten requirement: writes `cleaned_data`, idempotent), `state_estimation` (**#41**: the hand-written Kalman math moves into `transform` largely unchanged; delete the duplicate `StateEstimationService`).
6. **Signal explorer endpoint** + poller (needs Q1 answered).
7. **Docs**: rewrite `docs/ARCHITECTURE.md` (the backend now triggers the pipeline and reads Penelope), add `CLAUDE.md` / contributor guide.

---

## 8. Open questions

- **Q1. When is a run_id "ready" for the poller?** A run still receiving data shouldn't be processed half-way. Options:
  - no new Penelope rows for N minutes
  - an explicit end marker in Penelope (a car-state signal?)
  - manual trigger only until lap/stop detection exists
- **Q2. Frontend URL compatibility.** The frontend is out of scope, but renaming `/api/races` → `/api/v1/runs` and `race_id` → `run_id` breaks its hooks. Allow a small edit to `frontend/src/api` paths, or keep temporary legacy aliases?
- **Q3. How is penelope2 populated and kept fresh?** A one-off `pg_dump`/`restore` from Penelope, or a periodic sync job (possibly a pipeline step)? Who runs it, given Penelope needs the VPN?
- **Q4. `values[]` → signal mapping.** Need someone who knows the car to confirm the array index meanings per raw tag for `signal_sources` (GPS Location, IMU axes, etc.).
- **Q5. "X-axis = position".** For the signal explorer, should the x-axis be distance along the lap (1-D, comparable across laps) or the 2-D map position (coloring the track by signal value)? It affects the endpoint shape.
- **Q6. Root scratch files.** The untracked root `pyproject.toml`/`uv.lock`/`main.py`/`.python-version` (Python 3.14) conflict with the workspace root. Can these be replaced, with `sharktank.ipynb` moved to `notebooks/`?
