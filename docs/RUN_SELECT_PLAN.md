# Run Select Page: Plan

**Goal (today):** a frontend view where the user can

1. **Load a processed run**: pick from run ids that Orion has already processed.
2. **Process a new run**: pick a run id from Penelope that Orion hasn't processed and send it through the pipeline, then watch its status.

The frontend also gets typed hooks (axios + zod + TanStack Query) for **every pipeline stage**: clean, state estimation and metrics. This holds even for stages whose backend doesn't exist yet.

**Rule:** the browser only talks to the Orion backend (`/api/v1`). It never connects to Penelope or OrionDB directly. Database access stays in the backend and the pipeline service, using the existing clients and query builders.

---

## 1. What exists today

| Piece | State | Notes |
|---|---|---|
| `GET /api/v1/runs` | Done | Lists OrionDB `runs`. **But** `JobQueue.enqueue` inserts a `runs` row as soon as a job is *queued*, so this list includes runs that are queued, running or failed, not just processed ones. |
| `POST /api/v1/pipeline/runs` | Done | Backend → pipeline-api `POST /runs` → `pipeline_runs` row (`queued`). Returns `PipelineRunResponse`. |
| `GET /api/v1/pipeline/runs/{id}` | Done | One job's status (`queued / running / succeeded / failed`). |
| `GET /api/v1/pipeline/runs` | **Stub** | Backend route raises `NotImplementedError`; pipeline-api has no list route. |
| Listing Penelope runs | **Missing** | `penelope_tables.py` only declares `data` and `data_type`. Penelope's `run` table isn't modelled, and `PenelopeClient` has no `list_runs`. |
| Duplicate-job guard | **Missing** | Nothing stops queuing the same run twice. |
| Upstream error mapping | **Missing** | `PipelineService` calls `raise_for_status()`; a pipeline-api 404 or a connection error reaches the browser as a 500, not 404/502. |
| Pipeline steps | Partial | Only `clean_step` is registered. `state_step.py` and `lap_step.py` are empty; there is no metrics step. `PipelineRunner.run_step` / `run_from` raise `NotImplementedError`. |
| Per-step progress | **Missing** | No `pipeline_step_runs` table, so only job-level status is available. |
| Frontend | Scaffold | React + Vite + TS, a `fetch` client and a runs list. No axios, zod or TanStack Query yet. |

Penelope's `run` table (from the Penelope MCP docs; I couldn't verify it live because the VPN was off): `id` (uuid text), `"runId"` (small int counter), `"time"`, `"driverName"`, `"locationName"`, `notes`. **`data."runId"` joins to `run.id` (the uuid), not `run."runId"`.** Orion's `runs.run_id` and `PipelineRunResponse.run_id` (`UUID4`) both hold that uuid.

---

## 2. Proposed design

### 2.1 Data flow

```
Browser ──axios──▶ Vite proxy ──▶ orion-backend /api/v1
                                      │
              ┌───────────────────────┼─────────────────────────┐
              ▼                       ▼                         ▼
        OrionDB (async)      Penelope (read-only)       pipeline-api (HTTP)
   runs, pipeline_runs,      run table, async (D1)            │
   cleaned_data, state…                                       ▼
                                                     pipeline_runs queue
                                                              │
                                                    worker → PipelineRunner
                                                    PenelopeClient / OrionDBClient
```

### 2.2 Shared core (`packages/orion_core`)

- `models/penelope/penelope_tables.py`: add `run_table` (columns above, on `penelope_metadata`, so Alembic never touches it).
- `queries/penelope_queries.py`: add `select_penelope_runs(limit=None)`, newest first. Both the async backend and the sync `PenelopeClient` use this one builder.
- `queries/penelope_queries.py`: also add `select_penelope_runs_by_ids(ids)` for labelling processed runs (D6).
- `queries/orion_queries.py`: add `select_processed_runs()` (runs with a `succeeded`, error-free job, D2) and `select_processed_run_ids()`. Also add `select_pipeline_runs(run_id, status, limit)` for the job list, and `select_active_pipeline_run(run_id)` for the duplicate guard.

### 2.3 Pipeline service (`services/pipeline`)

- `PenelopeClient.list_runs() -> pd.DataFrame` using `select_penelope_runs()`. The worker's TODO (poll Penelope for new runs) needs this anyway.
- `JobQueue.list(run_id, status, limit)` and pipeline-api `GET /runs` so the backend's list stub can be implemented.
- Duplicate guard: `JobQueue.enqueue` refuses when the run already has a `queued`/`running` job. pipeline-api returns **409**, and the backend passes that through as 409.
- Per-step triggering is out of scope (D3).

### 2.4 Backend (`services/backend`)

| Route | Purpose | Source |
|---|---|---|
| `GET /api/v1/runs?processed=true` | Processed runs for the Load picker (D2), each with `run_time` from Penelope for the label (D6; `null` if Penelope is unreachable) | OrionDB via `RunRepository`, plus Penelope via `PenelopeRunRepository` |
| `GET /api/v1/penelope/runs` | Every Penelope run with `run_id` (uuid), `time`, and `processed: bool` (D7). 503 if Penelope isn't configured, 502 if unreachable. | Penelope via `PenelopeRunRepository` (async, D1), plus OrionDB for `processed` |
| `POST /api/v1/pipeline/runs` | Queue a run (exists). Add 409 / 502 mapping. | pipeline-api |
| `GET /api/v1/pipeline/runs?run_id=&status=&limit=` | Job history (implement the stub) | pipeline-api |
| `GET /api/v1/pipeline/runs/{id}` | Job status, polled by the frontend (exists). Add 404 / 502 mapping. | pipeline-api |

`PipelineService` gains error mapping: `httpx.ConnectError` → `UpstreamError` (502), 404 → `NotFoundError`, 409 → `AlreadyExistsError`. This follows the existing `core/exceptions.py` pattern.

### 2.5 Frontend (`frontend/src`)

New dependencies: `axios`, `zod`, `@tanstack/react-query`.

| Folder | Files | Notes |
|---|---|---|
| `api/` | `client.ts` | A single axios instance, `baseURL: '/api/v1'`. Replaces the current `fetch` client. An interceptor turns the backend's `ErrorResponse` into an `ApiError`. |
| `schemas/` *(new, D5)* | `run.schema.ts`, `penelopeRun.schema.ts`, `pipeline.schema.ts`, `cleanedData.schema.ts`, `state.schema.ts`, `metrics.schema.ts` | zod schemas plus `z.infer` types, mirroring the pydantic schemas. |
| `utils/` | `urls.ts` (`apiUrls`), `format.ts`, `describeError.ts` | `apiUrls` is the single place that knows URL paths. |
| `hooks/` | see the table below | Same shape as the example hook: `safeParse`, named return fields, query-key invalidation. |
| `views/` | `RunSelectView.tsx` | Two panels: **Load a processed run** and **Process a new run**. |
| `components/` | `RunSelect.tsx`, `PipelineJobStatus.tsx`, plus the existing state components | |
| `main.tsx` | wrap the app in `QueryClientProvider` | |

Path aliases (`@api`, `@hooks`, `@schemas`, `@utils`, `@components`, `@views`) go in both `tsconfig.app.json` and `vite.config.ts`, so imports match the example (`@api/client`).

**Hooks**

| File | Hooks | Backend status |
|---|---|---|
| `useRuns.ts` | `useRuns()`, `useRun(runId)`, `useRunMutations()` (delete) | exists |
| `usePenelopeRuns.ts` | `usePenelopeRuns()` | built in this plan |
| `usePipelineRuns.ts` | `usePipelineRuns(filters)`, `usePipelineRun(jobId)` (polls while `queued`/`running`), `usePipelineMutations()` → `triggerPipeline(runId)` | trigger and get exist; list is built in this plan |
| `useCleanedData.ts` | `useCleanedData(runId, range)` | **no backend route yet** |
| `useStateEstimation.ts` | `useStateEstimation(runId, range)` | `GET /runs/{id}/state` exists |
| `useMetrics.ts` | `useMetrics(runId)` | **no backend route or step yet** |

For stages with no backend yet, the hook and schema are written against the *planned* route. The hook returns a clear error ("not available yet") until the route exists, rather than faking data (D3).

A `CurrentRunContext` in `hooks/` (with a `useCurrentRun()` hook) holds the loaded run id (D4).

When a job **succeeds**, `usePipelineRun` invalidates `["runs"]` and `["penelope-runs"]`, so the run moves from the "process" list to the "load" list automatically.

### 2.6 Run Select view (UX)

- **Load a processed run:** a dropdown of processed runs (`00d5d5a4-… · Jul 11, 2026`) plus a **Load** button, which sets the current run (D4).
- **Process a run:** a dropdown of every Penelope run, in two `<optgroup>`s, **Not processed** and **Already processed** (re-run), plus a **Process** button. When an already-processed run is selected, a note says "This run has been processed before; processing replaces its data." After clicking, a status card shows the job (`queued → running → succeeded/failed`, with the error message on failure), polled every ~2 s until it finishes.
- **Penelope unavailable (VPN off):** the "process" panel shows "Penelope is unreachable" while the "load" panel keeps working.

---

## 3. Decisions

- **D1. Penelope access: the backend reads Penelope asynchronously.** The frontend calls `GET /api/v1/penelope/runs`. The backend reads Penelope's `run` table through an async Penelope reader (`PenelopeRunRepository`, the same route → service → repository pattern `GET /sensors` already uses). It shares the `select_penelope_runs()` builder with the pipeline's `PenelopeClient`, which also gets `list_runs()` for the worker's future poller. The SQL is written once and both sides run it.

  **Why async in the backend (but sync in the pipeline):**
  - *The backend is one event loop serving many small requests at once.* FastAPI runs every `async def` route on a single thread. A sync database call inside one (the pipeline's `PenelopeClient` is sync: psycopg plus pandas) **freezes that thread until Penelope answers**. Penelope sits behind the VPN, so it's often slow, and when the VPN is off a connect attempt hangs until it times out. During that wait every other request would stall, including the Load list (OrionDB) and the job-status poll that runs every 2 s. With an async driver (asyncpg), waiting on Penelope hands the thread back to the loop, and the other requests keep being served.
  - *It matches the rest of the backend.* The backend already opens Penelope and OrionDB with async engines (`core/database.py`), and `GET /sensors` reads Penelope this way. A sync client would mean a second database stack (and pandas) inside the backend just for one route.
  - *It keeps services independent.* Importing `orion_pipeline.clients.PenelopeClient` into the backend would make the API depend on the pipeline package and its heavy imports.
  - *The pipeline is the opposite workload.* It runs one long, CPU-bound pandas job at a time, so async buys it nothing (`REFACTOR_PLAN` D3). That's why its client is sync.
  - (The alternative would be calling the sync client from a plain `def` route, which FastAPI runs in a thread pool. That works, but it limits concurrency to the pool size and still brings the issues above.)
- **D2. "Processed" = the run has a `pipeline_runs` row with `status = 'succeeded'` and `error IS NULL`.** Queued, running and failed jobs don't count.
- **D3. Hooks: trigger and monitor jobs, and read every stage's output** (cleaned data, estimated state, metrics). No per-step triggering, so `run_step`/`run_from` stay out of scope. Hooks for stages without a backend route are written against the planned route and surface a clear "not available yet" error.
- **D4. Load sets a "current run"** in app state (a small React context) for later views to read. No routing yet.
- **D5. zod schemas live in `src/schemas/`**, imported as `@schemas/...`.
- **D6. Dropdown label: `<id> · <date>`**, using Penelope's `run.id` (the uuid every part of Orion uses) and `run.time`. Penelope's integer `"runId"` is ignored because it isn't unique. The processed-runs endpoint reads Penelope only for the date. If Penelope is unreachable, the Load list falls back to OrionDB `start_time`, so it still works off-VPN.
- **D7. Re-runs are allowed, but marked.** The Process picker lists every Penelope run in two groups: **Not processed** and **Already processed**, which is labelled clearly so a re-run is a deliberate choice.
- **D8. Status updates use polling** (`GET /pipeline/runs/{id}` every ~2 s while queued or running). This is assumed for today since the SSE endpoint is still a TODO; tell me if you want it changed.

---

## 4. Build order

1. `orion_core`: Penelope `run` table and query builders.
2. Pipeline: `PenelopeClient.list_runs`, `JobQueue.list`, duplicate guard, pipeline-api `GET /runs`.
3. Backend: `PenelopeRunRepository`/service/route (`GET /penelope/runs`), the processed-runs filter and labels, the pipeline list, and error mapping, with backend tests for each.
4. Frontend: dependencies, aliases, axios client, schemas, `apiUrls`, hooks, components, `RunSelectView`. Remove the old `useApi`/`useRuns` fetch hooks.
5. Verify: `npm run lint && npm run build`, backend `pytest`, then click through with `docker compose up` (needs VPN or `PENELOPE_DATABASE_URL` pointed at penelope2).
