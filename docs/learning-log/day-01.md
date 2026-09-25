# Day 1 — Foundations: secure setup & backend skeleton

## Phase 0 — Machine & repository setup

**Built:** free toolchain (Xcode CLT, Homebrew, gh, uv, fnm/Node, Docker CLI + Colima, gitleaks, pre-commit) and a public repo with a security-first scaffold.

| Concept | Where it's applied |
|---|---|
| **Git & GitHub Flow** — `main` always releasable; one branch per phase; merge via PR | Branch protection on `main`; PR #1 |
| **Secrets hygiene** — config via env vars; only placeholders are public | [`.gitignore`](../../.gitignore), [`.env.example`](../../.env.example) |
| **Shift-left security** — stop leaks *before* they enter history | [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml): gitleaks, private-key detection, noreply-email guard |
| **Defence in depth** — a second net on the server | GitHub secret scanning + push protection, Dependabot |
| **Architecture Decision Records** — record *why*, not *how* | [ADR 0001](../adr/0001-tech-stack.md) |

**Lesson learned:** never run destructive git commands (`git stash -u`, `git reset --hard`) in a repo with no commits — there is nothing to restore from. Commit first, then experiment.

## Phase 1 — Backend skeleton

**Built:** FastAPI app factory, typed settings, JSON logging, middleware stack, Problem Details errors, liveness endpoint, 19 tests, Makefile, CI.

```mermaid
flowchart LR
    C([curl / browser]) --> UV[uvicorn<br/>ASGI server] --> SH[Security headers] --> RC[Request context<br/>id · log · crash guard] --> CORS --> R[Router] --> H[Handler]
```

| Concept | What it means | Where it's applied |
|---|---|---|
| **Client–server** | The backend is a stateless JSON API; any client talks HTTP to it | [`app/main.py`](../../backend/app/main.py) |
| **ASGI & async** | uvicorn accepts connections; one process serves many requests while each awaits I/O | `make dev` |
| **Request/response lifecycle** | Request → middleware (outer→inner) → route → response → middleware (inner→outer) | [`core/middleware.py`](../../backend/app/core/middleware.py) |
| **Middleware** | Cross-cutting logic written once, applied to every request | Request ID, access log, CORS, security headers |
| **12-factor config** | Settings come from the environment, validated at startup (fail fast) | [`core/config.py`](../../backend/app/core/config.py) |
| **Structured logging** | JSON lines, correlated by `request_id`, secrets redacted | [`core/logging.py`](../../backend/app/core/logging.py) |
| **Exception handling** | Domain errors → one standard shape (RFC 9457); crashes → generic 500 | [`core/errors.py`](../../backend/app/core/errors.py) |
| **Dependency injection** | Components receive what they need (e.g. `create_app(settings)`), so tests swap in fakes | [`tests/conftest.py`](../../backend/tests/conftest.py) |
| **Ports** | API 8000 · frontend 5173 · Postgres 5432 · Redis 6379 | [`Makefile`](../../Makefile) |
| **Lockfiles & reproducibility** | `uv.lock` pins every package version for laptop, CI and Docker | [`backend/uv.lock`](../../backend/uv.lock) |
| **CI** | Every PR is checked on a clean machine; actions pinned to SHAs, read-only token | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) |

**Security details worth remembering**

- Validation errors return field names only — never the submitted values (a rejected password is not echoed).
- Client-supplied `X-Request-ID` values are accepted only if short and alphanumeric, preventing log injection.
- The `Server` header is removed, and API docs are disabled in production.
- `make env` generates random secrets; `.env` is created with `600` permissions.

**Not applicable yet:** database readiness check (Phase 2), rate limiting (Phase 3, needs Redis).
