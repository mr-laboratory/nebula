# ADR 0001 — Tech stack

- **Status:** Accepted
- **Date:** 2026-09-25

## Context

Nebula is a bootcamp project that must be production-grade, use only free tools, run locally for the demo, and apply Day 1–5 concepts (API design, databases, auth, testing, observability).

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

- **Django REST Framework** — heavier; less aligned with async FastAPI curriculum.
- **SQLite** — no partial indexes / concurrency realism for production.
- **Streamlit** — great for data apps, not for multi-user auth + custom UI.
- **Snowflake** — analytics warehouse, not an OLTP app database; paid.
- **Docker Desktop** — licence restrictions; Colima is free.

## Consequences

More moving parts (DB, Redis, frontend) than a toy app, offset by Docker Compose and a Makefile for one-command setup.
