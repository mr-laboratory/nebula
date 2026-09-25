# 🌌 Nebula

> Where ideas take shape.

A production-grade, user-specific blog platform.

## Features

- Public feed and post pages (no login needed)
- Sign up / sign in with secure, short-lived tokens
- Authors create, edit, publish and delete **their own** posts (drafts stay private)
- Likes and comments from other signed-in users
- Responsive, futuristic dark UI

## Tech stack

FastAPI · SQLAlchemy 2 (async) · Alembic · PostgreSQL · Redis · React + Vite + TypeScript · Tailwind CSS · shadcn/ui · Docker Compose · GitHub Actions

## Documentation

- [Architecture](docs/architecture.md)
- [API reference](docs/api.md)
- [Database](docs/database.md)
- [Architecture decisions](docs/adr/)

## Quickstart

**Prerequisites:** [uv](https://docs.astral.sh/uv/), `make`, [pre-commit](https://pre-commit.com/), and Docker (Docker Desktop, or [Colima](https://github.com/abiosoft/colima) on macOS).

```bash
git clone https://github.com/mr-laboratory/nebula.git && cd nebula
make setup    # install dependencies + git hooks, create .env with random secrets
make db-up    # start Postgres + Redis
make migrate  # create the schema
make seed     # optional: demo users, posts, likes and comments
make dev      # API on http://localhost:8000 — interactive docs at /docs
```

| Command | Purpose |
|---|---|
| `make test` | Run the test suite |
| `make lint` / `make fmt` | Check / fix style |
| `make typecheck` | Static type checking (mypy, strict) |
| `make check` | Everything CI runs |
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
│   ├── services/          # business logic
│   └── api/               # dependencies and v1 HTTP endpoints
├── migrations/            # Alembic schema migrations
├── scripts/               # developer scripts (seed data)
└── tests/
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
