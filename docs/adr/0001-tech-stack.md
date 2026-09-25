# ADR 0001 — Tech stack

- **Status:** Accepted
- **Date:** 2026-09-25

## Context

Nebula must be production-grade, built entirely on free and open-source tooling, and runnable locally with a single command. It needs a clean API design, a relational data model, secure authentication, automated tests and observability.

## Decision

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI + Pydantic v2 | Async, typed, auto OpenAPI docs |
| ORM / migrations | SQLAlchemy 2 (async) + Alembic | Industry standard, versioned schema |
| Database | PostgreSQL 16 | Relational integrity, partial indexes, EXPLAIN ANALYZE |
| Cache / rate limit | Redis | Fast counters and caching |
| Auth | Argon2id + JWT access + rotating refresh cookie | Secure, stateless reads, revocable sessions |
| Frontend | React + Vite + TypeScript, Tailwind, shadcn/ui, Motion | Fast, modern, polished UI |
| Tooling | uv, ruff, mypy, pytest, pre-commit, gitleaks | Fast installs, quality gates, secret safety |
| Runtime | Docker Compose on Colima | Free (Docker Desktop needs a licence) |
| CI | GitHub Actions | Free for public repos |

## Alternatives considered

- **Django REST Framework** — heavier and sync-first; FastAPI gives native async and typed OpenAPI docs.
- **SQLite** — no partial indexes / concurrency realism for production.
- **Streamlit** — great for data apps, not for multi-user auth + custom UI.
- **Snowflake** — analytics warehouse, not an OLTP app database; paid.
- **Docker Desktop** — licence restrictions; Colima is free.

## Consequences

More moving parts (DB, Redis, frontend) than a toy app, offset by Docker Compose and a Makefile for one-command setup.
