# 🌌 Nebula

> Where ideas take shape.

A production-grade, user-specific blog platform.

## Features

- Public feed and post pages (no login needed)
- Sign up / sign in with secure, short-lived tokens
- Authors create, edit, publish and delete **their own** posts (drafts stay private)
- Likes and comments from other signed-in users
- Markdown editor with live preview, tags and an unsaved-changes guard
- Responsive UI with light, dark and system themes, and generated cover art

## Tech stack

FastAPI · SQLAlchemy 2 (async) · Alembic · PostgreSQL · Redis · React 19 + Vite + TypeScript · Tailwind CSS v4 · TanStack Query · Motion · Docker Compose · GitHub Actions

## Documentation

- [Architecture](docs/architecture.md)
- [API reference](docs/api.md)
- [Database](docs/database.md)
- [Architecture decisions](docs/adr/)

## Quickstart

**Prerequisites:** [uv](https://docs.astral.sh/uv/), [Node.js 24+](https://nodejs.org/), `make`, [pre-commit](https://pre-commit.com/), and Docker (Docker Desktop, or [Colima](https://github.com/abiosoft/colima) on macOS).

```bash
git clone https://github.com/mr-laboratory/nebula.git && cd nebula
make setup    # install dependencies + git hooks, create .env with random secrets
make db-up    # start Postgres + Redis
make migrate  # create the schema
make seed     # optional: demo users, posts, likes and comments
make dev      # API on http://localhost:8000 — interactive docs at /docs
make web      # in a second terminal: app on http://localhost:5173
```

| Command | Purpose |
|---|---|
| `make test` | Run the test suite |
| `make lint` / `make fmt` | Check / fix style |
| `make typecheck` | Static type checking (mypy, strict) |
| `make web-check` | Lint, type-check, test and build the web app |
| `make check` | Everything CI runs (backend and web app) |
| `make api-types` | Regenerate the OpenAPI schema and the frontend's API types |
| `make db-up` / `make db-down` | Start / stop Postgres and Redis |
| `make migration m="…"` | Generate a migration from model changes |
| `make psql` | SQL shell on the local database |

## Project structure

```
backend/
├── app/
│   ├── main.py            # application factory
│   ├── core/              # config, logging, middleware, errors, security, rate limits
│   ├── db/                # declarative base, engine and sessions
│   ├── models/            # ORM models (one file per table group)
│   ├── schemas/           # request/response models (whitelisted fields)
│   ├── services/          # business logic and permission checks
│   ├── repositories/      # database queries (filters, pagination, eager loading)
│   └── api/               # dependencies and v1 HTTP endpoints
├── migrations/            # Alembic schema migrations
├── scripts/               # developer scripts (seed data)
└── tests/
frontend/
├── public/                # favicon, pre-paint theme script
└── src/
    ├── api/               # HTTP client (token refresh), endpoints, generated types
    ├── auth/              # session provider and route guard
    ├── theme/             # light / dark / system mode
    ├── components/        # layout, cards, cover art, Markdown, comments, UI primitives
    ├── pages/             # feed, post, editor, dashboard, profile, sign-in
    └── lib/               # pure helpers (drafts, tags, permissions, covers) with tests
docker/                    # container init scripts
docs/                      # architecture, API, database, ADRs
docker-compose.yml         # local Postgres + Redis
```

## Security

Found a vulnerability? Please follow [SECURITY.md](SECURITY.md) and **do not** open a public issue.

## About

Built as part of the AI Bootcamp Week 1 assignment.

## License

[MIT](LICENSE)
