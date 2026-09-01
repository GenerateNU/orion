# orion

React (Vite) frontend + FastAPI backend, run with Docker Compose.

## Quick Start

```bash
cp .env.example .env && docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000

Both services hot-reload on file changes. Frontend requests to `/api/*` are
proxied to the backend.

## Layout

```
backend/    FastAPI app (main.py)
frontend/   React app (src/App.jsx)
```
