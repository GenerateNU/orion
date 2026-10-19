# orion

Orion turns NER's raw car telemetry into clean, analysis-ready data and shows it
on a web dashboard.

The car's sensor readings are published to **Penelope**, NER's telemetry
database. That data is raw: sensor names are inconsistent, timestamps from some
sources are offset, and nothing is derived yet. Orion reads Penelope (it never
writes to it), runs each run through a processing pipeline, stores the results in
its own database (**OrionDB**), and serves them to a React dashboard.

## What it does

- **Browse runs.** See every run recorded in Penelope and which ones Orion has
  already processed.
- **Process a run.** Trigger the pipeline for a run from the dashboard and watch
  its status. Jobs are queued and handled in the background, and re-running a run
  replaces its old output.
- **Explore sensor data.** View a run's sensor readings under consistent, clean
  sensor names and units.

## The pipeline

Each run goes through a series of steps. Each step reads the previous step's
output and saves its own, so any step can be re-run on its own.

| Step                | What it produces                                                   | Status      |
| ------------------- | ------------------------------------------------------------------ | ----------- |
| Clean               | Raw readings mapped to clean sensor names and units, GPS time corrected | Done        |
| State estimation    | Estimated car state over the run                                   | Not started |
| Laps                | Lap detection and per-lap data                                     | Not started |

## How it fits together

```
browser ──► dashboard ──► API ──► OrionDB      (Orion's own data)
                           │  └─► Penelope     (raw telemetry, read-only)
                           ▼
                     pipeline API ──► job queue ──► pipeline worker
                                                     reads Penelope,
                                                     writes OrionDB
```

- **Dashboard** (`frontend/`): React app for browsing runs, triggering the
  pipeline, and viewing data.
- **API** (`services/backend/`): serves runs, sensors, and pipeline status to the
  dashboard.
- **Pipeline** (`services/pipeline/`): an API that queues processing jobs, and a
  worker that runs them.
- **Shared core** (`packages/orion_core/`): settings, database models, and
  queries used by both services.

## Getting started

You need Docker and a connection string for Penelope (the real database over the
NER VPN, or `penelope2`, a copy hosted on Neon).

```bash
cp .env.example .env        # set PENELOPE_DATABASE_URL
docker compose up --build
docker compose exec orion-backend python -m orion_core.db.scripts.seed_sensors   # once
```

Then open the dashboard at http://localhost:5173.

## Documentation

- [DevREADME.md](DevREADME.md): architecture, services, configuration, local
  development, migrations, and CI.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): design notes.
