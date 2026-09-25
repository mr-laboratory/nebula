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
- [Architecture decisions](docs/adr/)

## Quickstart

**Prerequisites:** [uv](https://docs.astral.sh/uv/), `make`, and [pre-commit](https://pre-commit.com/).

```bash
git clone https://github.com/mr-laboratory/nebula.git && cd nebula
make setup    # install dependencies + git hooks, create .env with random secrets
make dev      # API on http://localhost:8000 — interactive docs at /docs
```

| Command | Purpose |
|---|---|
| `make test` | Run the test suite |
| `make lint` / `make fmt` | Check / fix style |
| `make typecheck` | Static type checking (mypy, strict) |
| `make check` | Everything CI runs |

## Project structure

```
backend/
├── app/
│   ├── main.py            # application factory
│   ├── core/              # config, logging, middleware, errors
│   └── api/v1/routes/     # HTTP endpoints
└── tests/
docs/                      # architecture, ADRs
```

## Security

Found a vulnerability? Please follow [SECURITY.md](SECURITY.md) and **do not** open a public issue.

## About

Built as part of the AI Bootcamp Week 1 assignment.

## License

[MIT](LICENSE)
