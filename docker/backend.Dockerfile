# Backend image: the backend, the pipeline API and the pipeline worker, started
# together by docker/entrypoint.sh. The frontend has its own image (frontend.Dockerfile).
# Built from the repo root.

FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first (cached layer): uv needs every member's pyproject to resolve the workspace.
COPY pyproject.toml uv.lock .python-version ./
COPY packages/orion_core/pyproject.toml packages/orion_core/
COPY services/backend/pyproject.toml services/backend/
COPY services/pipeline/pyproject.toml services/pipeline/
RUN uv sync --frozen --no-dev --all-packages --no-install-workspace

COPY packages packages
COPY services services
RUN uv sync --frozen --no-dev --all-packages

COPY docker/entrypoint.sh /usr/local/bin/orion-entrypoint

EXPOSE 8000
CMD ["orion-entrypoint"]
