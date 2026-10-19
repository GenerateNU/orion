# Orion Makefile
# Works on: macOS, Linux, Windows (PowerShell, cmd, or Git Bash)
# Requires: Git Bash on Windows (comes with Git for Windows), Docker, uv

# Detect OS and set shell accordingly
ifeq ($(OS),Windows_NT)
    # Windows: run every recipe through Git Bash
    SHELL := C:/Program Files/Git/bin/bash.exe
    # Fallback for the 32-bit install location
    ifeq ($(wildcard $(SHELL)),)
        SHELL := C:/Program Files (x86)/Git/bin/bash.exe
    endif
else
    SHELL := /bin/bash
endif
.SHELLFLAGS := -euo pipefail -c

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
NC := \033[0m

DOCKER_COMPOSE := docker compose
DB_SERVICE := orion-db
BACKEND_SERVICE := orion-backend
ALEMBIC := alembic -c packages/orion_core/alembic.ini

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@printf "$(BLUE)Orion$(NC)\n"
	@echo "Usage: make <target>"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Run a command in the backend container if it's up, otherwise locally with uv
define run_cmd
	if $(DOCKER_COMPOSE) ps -q $(BACKEND_SERVICE) 2>/dev/null | head -n1 | grep -q .; then \
		printf "$(CYAN)Running in Docker...$(NC)\n"; \
		$(DOCKER_COMPOSE) exec $(BACKEND_SERVICE) $(1); \
	else \
		printf "$(CYAN)Running locally...$(NC)\n"; \
		uv run $(1); \
	fi
endef

# ==================== Environment ====================

.PHONY: install
install: ## Install all workspace packages into .venv
	@uv sync
	@printf "$(GREEN)✓ Installed$(NC)\n"

.PHONY: up
up: ## Start the new stack (db, migrations, backend, pipeline API + worker)
	@printf "$(YELLOW)Starting services...$(NC)\n"
	@$(DOCKER_COMPOSE) up -d --build orion-backend orion-pipeline-api orion-pipeline-worker
	@printf "$(GREEN)✓ Services started$(NC)\n"
	@echo "Backend docs:  http://localhost:8100/docs"
	@echo "Pipeline docs: http://localhost:8200/docs"
	@echo "Database:      localhost:5434"

.PHONY: down
down: ## Stop all services
	@$(DOCKER_COMPOSE) down
	@printf "$(GREEN)✓ Services stopped$(NC)\n"

.PHONY: restart
restart: ## Restart all services
	@$(MAKE) down && $(MAKE) up

.PHONY: logs
logs: ## Follow logs for the new stack
	@$(DOCKER_COMPOSE) logs -f orion-backend orion-pipeline-api orion-pipeline-worker

.PHONY: status
status: ## Show service status
	@$(DOCKER_COMPOSE) ps

# ==================== Database ====================

.PHONY: migrate
migrate: ## Apply pending migrations
	@printf "$(YELLOW)Running migrations...$(NC)\n"
	@$(call run_cmd,$(ALEMBIC) upgrade head)
	@printf "$(GREEN)✓ Migrations applied$(NC)\n"

.PHONY: migration
migration: ## Autogenerate a migration from model changes (prompts for a name)
	@printf "$(YELLOW)Enter migration name: $(NC)" && read name && \
	if [ -z "$$name" ]; then \
		printf "$(RED)✗ Migration name cannot be empty$(NC)\n" >&2; exit 1; \
	fi; \
	$(call run_cmd,$(ALEMBIC) revision --autogenerate -m "$$name"); \
	printf "$(GREEN)✓ Migration created in packages/orion_core/alembic/versions$(NC)\n"

.PHONY: shell
shell: ## Open psql on the local OrionDB
	@$(DOCKER_COMPOSE) exec $(DB_SERVICE) psql -U orion -d orion

# ==================== Pipeline ====================

.PHONY: pipeline-run
pipeline-run: ## Run the pipeline for one run now: make pipeline-run RUN_ID=<id>
	@if [ -z "$${RUN_ID:-}" ]; then printf "$(RED)✗ Usage: make pipeline-run RUN_ID=<id>$(NC)\n" >&2; exit 1; fi
	@$(call run_cmd,orion-pipeline run $(RUN_ID))

# ==================== Code Quality ====================

.PHONY: test
test: ## Run tests
	@uv run pytest

.PHONY: lint
lint: ## Lint (ruff check + pydoclint)
	@uv run ruff check packages services
	@uv run pydoclint packages services

.PHONY: format-check
format-check: ## Check formatting (ruff format --check)
	@uv run ruff format --check packages services

.PHONY: typecheck
typecheck: ## Type check (mypy)
	@uv run mypy

# Runs every tool even if an earlier one fails, so one pass shows everything left to fix.
.PHONY: format
format: ## Auto-fix lint and formatting, then report docstring and type errors
	@status=0; \
	uv run ruff check --fix packages services || status=1; \
	uv run ruff format packages services || status=1; \
	uv run pydoclint packages services || status=1; \
	uv run mypy || status=1; \
	if [ $$status -eq 0 ]; then printf "$(GREEN)✓ All checks pass$(NC)\n"; \
	else printf "$(RED)✗ Fix the errors above by hand$(NC)\n" >&2; fi; \
	exit $$status

.PHONY: quality
quality: lint format-check typecheck test ## Lint, format check, type check, and tests (what CI runs)
