# Developer commands. Run `make` to list them.
.DEFAULT_GOAL := help
BACKEND := cd backend &&

.PHONY: help setup env dev test lint fmt typecheck check db-up db-down migrate migration seed psql

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
	$(BACKEND) uv run mypy app tests scripts migrations

check: lint typecheck test ## Everything CI runs

db-up: ## Start Postgres + Redis (starts Colima first if installed)
	@if command -v colima >/dev/null; then colima status >/dev/null 2>&1 || colima start; fi
	docker compose up -d --wait

db-down: ## Stop Postgres + Redis (data is kept)
	docker compose down

migrate: ## Apply all pending migrations
	$(BACKEND) uv run alembic upgrade head

migration: ## Autogenerate a migration: make migration m="add x"
	@test -n "$(m)" || (echo 'usage: make migration m="describe the change"' && exit 1)
	$(BACKEND) uv run alembic revision --autogenerate -m "$(m)"

seed: ## Reset and fill the local DB with demo data
	$(BACKEND) uv run python -m scripts.seed --reset

psql: ## Open a psql shell on the local DB
	docker compose exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'
