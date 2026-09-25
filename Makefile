# Developer commands. Run `make` to list them.
.DEFAULT_GOAL := help
BACKEND := cd backend &&

.PHONY: help setup env dev test lint fmt typecheck check

help: ## Show available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: env ## Install dependencies and git hooks
	$(BACKEND) uv sync
	pre-commit install

env: ## Create .env with random secrets (if missing)
	@scripts/init-env.sh

dev: ## Run the API with auto-reload on :8000
	$(BACKEND) uv run uvicorn app.main:create_app --factory --reload --port 8000 --no-server-header

test: ## Run tests
	$(BACKEND) uv run pytest

lint: ## Lint and check formatting
	$(BACKEND) uv run ruff check . && uv run ruff format --check .

fmt: ## Auto-fix lint issues and format
	$(BACKEND) uv run ruff check --fix . && uv run ruff format .

typecheck: ## Static type check
	$(BACKEND) uv run mypy app tests

check: lint typecheck test ## Everything CI runs
