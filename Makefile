# Developer commands. Run `make` to list them.
.DEFAULT_GOAL := help
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.PHONY: help setup env dev web up down logs smoke test lint fmt typecheck check web-check api-types db-up db-down migrate migration seed seed-large explain grant revoke psql backup restore

help: ## Show available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: env ## Install dependencies and git hooks
	$(BACKEND) uv sync
	$(FRONTEND) npm ci
	pre-commit install

env: ## Create .env with random secrets (if missing)
	@scripts/init-env.sh

dev: ## Run the API with auto-reload on :8000
	$(BACKEND) uv run uvicorn app.main:create_app --factory --reload --port 8000 --no-server-header

web: ## Run the web app with hot reload on :5173 (proxies /api to :8000)
	$(FRONTEND) npm run dev

up: env ## Build and run the whole app in Docker on http://localhost:8080
	@if command -v colima >/dev/null; then colima status >/dev/null 2>&1 || colima start; fi
	docker compose --profile app up -d --build --wait
	@echo "✓ Nebula is running on http://localhost:$${WEB_PORT:-8080}"

down: ## Stop every container (data is kept)
	docker compose --profile app down

smoke: ## Check the running Docker stack end to end
	@scripts/smoke-test.sh

logs: ## Follow the API and web logs (Ctrl-C to stop)
	docker compose --profile app logs -f api web

test: ## Run tests
	$(BACKEND) uv run pytest

lint: ## Lint and check formatting
	$(BACKEND) uv run ruff check . && uv run ruff format --check .

fmt: ## Auto-fix lint issues and format
	$(BACKEND) uv run ruff check --fix . && uv run ruff format .

typecheck: ## Static type check
	$(BACKEND) uv run mypy app tests scripts migrations

web-check: ## Lint, format check, type check, test and build the web app
	$(FRONTEND) npm run check

check: lint typecheck test web-check ## Everything CI runs

api-types: ## Re-export the OpenAPI schema and regenerate the frontend's API types
	$(BACKEND) uv run python -m scripts.export_openapi > ../docs/openapi.json
	$(FRONTEND) npm run api-types && npx prettier --write src/api/schema.d.ts >/dev/null

db-up: ## Start Postgres + Redis (starts Colima first if installed)
	@if command -v colima >/dev/null; then colima status >/dev/null 2>&1 || colima start; fi
	docker compose up -d --wait

db-down: ## Stop Postgres + Redis, and the app if it's running (data is kept)
	docker compose --profile app down

migrate: ## Apply all pending migrations
	$(BACKEND) uv run alembic upgrade head

migration: ## Autogenerate a migration: make migration m="add x"
	@test -n "$(m)" || (echo 'usage: make migration m="describe the change"' && exit 1)
	$(BACKEND) uv run alembic revision --autogenerate -m "$(m)"

seed: ## Reset and fill the local DB with demo data
	$(BACKEND) uv run python -m scripts.seed --reset

seed-large: ## Reset and fill the local DB with ~10k posts (for query tuning)
	$(BACKEND) uv run python -m scripts.seed --reset --users 500 --posts-per-user 20

explain: ## Print EXPLAIN ANALYZE timings for the hot queries (run after seed-large)
	$(BACKEND) uv run python -m scripts.explain

grant: ## Give a user a role: make grant u=alice role=admin
	@test -n "$(u)" -a -n "$(role)" || (echo 'usage: make grant u=<username> role=<role>' && exit 1)
	$(BACKEND) uv run python -m scripts.roles grant "$(u)" "$(role)"

revoke: ## Take a role away: make revoke u=alice role=moderator
	@test -n "$(u)" -a -n "$(role)" || (echo 'usage: make revoke u=<username> role=<role>' && exit 1)
	$(BACKEND) uv run python -m scripts.roles revoke "$(u)" "$(role)"

psql: ## Open a psql shell on the local DB
	docker compose exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

backup: ## Dump the local DB to backups/ (git-ignored)
	@scripts/backup.sh

restore: ## Replace the local DB with a dump: make restore f=backups/<file>.dump
	@scripts/restore.sh "$(f)"
