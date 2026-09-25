# Nebula — Production-Grade Blog Platform: End-to-End Build Plan

> Week 1 project, AI Bootcamp (Software Engineering Crash Course)
> Working name: **Nebula** (rename freely)

---

## 0. The Assignment, Decoded

| Requirement | What it means technically |
|---|---|
| Anyone can browse & read **published** blogs without login | Public `GET` endpoints; only `status=published` & not soft-deleted posts visible |
| Authenticated users create & manage **their own** blogs | JWT auth + **resource ownership** (`author_id == current_user.id`) on update/delete; drafts visible only to owner |
| **Other** logged-in users can like & comment | Auth-required `POST` for likes/comments; one like per user per post (composite PK) |
| Production GitHub repo, modular, clean README | Layered architecture, tests, CI, Docker, `.env.example`, Makefile |
| 2-minute demo video | Scripted flow (Section 8) |
| Architecture + API contracts + usage guide | `docs/` folder + auto-generated OpenAPI (Swagger) |

**Rule of thumb for the week:** the *core* (auth + posts + likes + comments + docs) must be rock solid. Everything from Day 4/5 (uploads, caching, RBAC, observability) is layered on top as "production polish". If time runs short, cut from the bottom of the list, never the core.

---

## 1. Tech Stack (and why)

| Layer | Choice | Why this (vs alternatives) |
|---|---|---|
> **Constraint: 100% free.** Everything below is open-source or free-tier-with-no-card. No paid licences.

| Language | **Python 3.12+** | Matches bootcamp prerequisites |
| API framework | **FastAPI** | Async, dependency injection, Pydantic validation, automatic OpenAPI/Swagger (= free API contract docs). DRF is heavier for a 1-week build |
| Validation / schemas | **Pydantic v2** + `pydantic-settings` | Request/response schemas + typed env config |
| ORM | **SQLAlchemy 2.0 (async)** | Industry standard; explicit control over eager/lazy loading (Day 4 N+1 topic) |
| Migrations | **Alembic** | Versioned schema changes (prereq: migrations) |
| Database | **PostgreSQL 16** | Real constraints, indexes, `EXPLAIN ANALYZE`, full-text search. SQLite hides too much |
| Cache / rate limit | **Redis 7** | Response caching + rate-limit counters (Day 4) |
| Password hashing | **pwdlib[argon2]** (Argon2id) | Modern, what FastAPI docs now recommend (passlib is unmaintained) |
| Tokens | **PyJWT** | Access JWT + rotating refresh token |
| Package manager | **uv** (Python), **npm** (frontend) | uv is fast, lockfile-based, manages venvs (Day 1 package managers) |
| Lint / format / types | **ruff**, **mypy**, **pre-commit** | Automated quality gate before every commit |
| Tests | **pytest**, **pytest-asyncio**, **httpx** | API tests against a real Postgres (in CI via service container) |
| Frontend | **React 19 + Vite + TypeScript**, TanStack Query, React Router | Real client-server split (Day 1) + permission-based UI (Day 5) |
| UI kit | **Tailwind CSS v4** + **shadcn/ui** (Radix primitives) + **Motion** (animations) + **Lucide** icons + **Sonner** toasts | All MIT/free. Futuristic dark-first theme, accessible, small bundle |
| Third-party API | **Unsplash API** (free dev key) for cover-image search; fallback **Picsum** (no key). Stretch: **GitHub OAuth** login (free) | API keys, secrets, timeouts, retries, rate limits (Unsplash free = 50 req/h, perfect for demonstrating 429 handling), data mapping; OAuth2 (Day 2) |
| Containers | **Docker CLI + Compose on Colima** (free, open-source runtime) | Docker Desktop needs a paid licence at larger companies, so we avoid it |
| CI/CD | **GitHub Actions** (free for public repos) + GHCR | Lint → type-check → test → build on every PR |
| Observability | JSON structured logs + request IDs, `/health/live` & `/health/ready`, Prometheus `/metrics`, error tracking via structured exception logs (optional self-hosted **GlitchTip**, Sentry-compatible & free) | Day 5 logs/metrics/error tracking |
| API testing | Swagger UI (built-in) + **Bruno** (free, open-source Postman alternative) | Collections committed to repo |
| Demo recording | macOS **Cmd+Shift+5** (built-in) or Loom free tier (5-min limit is fine) | |

---

## 1b. UI / UX Direction: "Futuristic, light, awesome"

- **Responsive web app**, mobile-first (phone → tablet → desktop breakpoints), works in any browser.
- **Theme**: dark-first "cosmic" look: deep navy/black background with a subtle animated **aurora gradient**, **glassmorphism** cards (translucent + backdrop blur), **neon accent** gradient (cyan → violet → magenta), glowing focus rings. Light mode toggle included.
- **Typography**: *Space Grotesk* (headings) + *Inter* (body) + *JetBrains Mono* (code), all Google Fonts (free).
- **Motion**: page transitions, card hover lift/glow, animated like "burst", skeleton shimmer loaders. Respects `prefers-reduced-motion`.
- **Key screens**: Landing/feed (hero + trending + tag chips), post reader (clean reading mode, reading-time, sticky like/comment bar), markdown editor with live split preview & cover picker (Unsplash search), author dashboard (stats cards: views/likes/comments, drafts vs published), profile page, auth pages, command palette (⌘K search).
- **"Lighter"** means a small JS bundle (Vite code-splitting, no heavy UI framework), and every screen fast. It does **not** mean fewer features.

---

## 1c. Scope Tiers: what's required vs what the curriculum adds

| Tier | Included | Would I build it without the day-wise curriculum? |
|---|---|---|
| **A: Assignment core** | Public feed/read, register/login, own-post CRUD + drafts, likes, comments, README, docs, demo | Yes, mandatory |
| **B: Production baseline** | Layered architecture, Postgres + migrations, validation, consistent errors, pagination, JWT+refresh, ownership tests, rate-limit on login, logging, health check, Docker Compose, CI | Yes. "Production grade" means this |
| **C: Curriculum extras** | Cover image upload, CSV export, indexes + EXPLAIN, N+1 fix, Redis cache, Unsplash integration, RBAC (user/moderator/admin), audit logs, metrics, backups | Mostly no. Added (in light form) because they're the week's topics |
| **Decision (2026-09-25)** | Build **A + B first**, then **two committed C items**: (1) indexes + N+1 fix with EXPLAIN ANALYZE before/after, (2) simple roles `user`/`moderator` (moderator can delete any comment/post). Remaining C items only if time permits (architecture leaves hooks so none needs a rewrite) | |
| **Dropped for lightness** | PDF export, S3/MinIO, full admin UI, real multi-tenant orgs | Documented in learning log as "understood, not applied" |

---

## 2. System Architecture

```
┌──────────────┐   HTTPS/JSON    ┌─────────────────────────────────────────────┐
│ React SPA    │ ──────────────► │ FastAPI (uvicorn)                            │
│ (Vite, :5173)│ ◄────────────── │  Middleware: RequestID → Logging → CORS →    │
└──────────────┘  Bearer JWT +   │              GZip → RateLimit                │
                  refresh cookie │  Routers (controllers)  /api/v1/...          │
                                 │      │  Depends(): get_db, get_current_user, │
                                 │      ▼            require_permission(...)    │
                                 │  Services (business rules, ownership)        │
                                 │      ▼                                       │
                                 │  Repositories (all SQL lives here)           │
                                 └──────┬──────────────┬───────────────┬────────┘
                                        ▼              ▼               ▼
                                  PostgreSQL        Redis        Local storage / S3
                                                                (cover images)
                                        Integrations: Claude API (summaries)
```

### Layering (MVC adapted to an API — Day 2)

| MVC concept | Where it lives here | Rule |
|---|---|---|
| **Model** | `app/models/` (SQLAlchemy) | Tables, relationships, constraints |
| **View** | `app/schemas/` (Pydantic response models) + React UI | Shape of output only, no logic |
| **Controller** | `app/api/v1/routes/` | Parse request → call service → return schema. *Thin.* |
| **Service** | `app/services/` | Business rules: "only owner can edit", "can't like twice" |
| **Repository** | `app/repositories/` | DB queries only. Services never write raw SQL |

Dependency direction: `routes → services → repositories → models`. Never the reverse. This is the "dependency boundaries" topic.

### Repository layout

```
nebula/
├── backend/
│   ├── app/
│   │   ├── main.py                 # app factory, middleware, router registration
│   │   ├── core/                   # config.py, security.py, logging.py, errors.py, permissions.py
│   │   ├── db/                     # base.py (Base, mixins), session.py
│   │   ├── models/                 # user.py, role.py, post.py, comment.py, like.py, tag.py, audit.py
│   │   ├── schemas/                # auth.py, user.py, post.py, comment.py, common.py (pagination, errors)
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── integrations/           # ai_client.py (Claude), with timeout/retry
│   │   ├── storage/                # base.py (interface), local.py, s3.py (optional)
│   │   └── api/
│   │       ├── deps.py             # get_db, get_current_user, optional_user, require_permission
│   │       └── v1/routes/          # auth, users, posts, comments, likes, uploads, exports, admin, health
│   ├── alembic/                    # migrations
│   ├── tests/                      # unit/ + api/ ; conftest.py with test DB
│   ├── scripts/seed.py
│   ├── pyproject.toml, uv.lock
│   └── Dockerfile
├── frontend/                       # Vite React TS app
├── docs/
│   ├── architecture.md             # diagrams, layers, request lifecycle, auth flow
│   ├── api.md                      # API contracts (+ link to /docs Swagger)
│   ├── database.md                 # ERD, indexes, EXPLAIN results
│   ├── usage.md                    # user guide
│   ├── adr/                        # Architecture Decision Records (why JWT, why Postgres...)
│   └── learning-log/               # day-01.md ... day-05.md  ← your bootcamp journal
├── scripts/backup_db.sh, restore_db.sh
├── .github/workflows/ci.yml
├── .github/pull_request_template.md
├── docker-compose.yml
├── Makefile
├── .env.example
├── .pre-commit-config.yaml
└── README.md
```

---

## 3. Database Design (prereq: schema design)

### Tables

| Table | Key columns | Notes (concept) |
|---|---|---|
| `users` | `id` UUID PK, `email` UNIQUE, `username` UNIQUE, `password_hash`, `display_name`, `bio`, `is_active`, audit fields | Never store plain passwords |
| `roles` | `id`, `name` UNIQUE (`user`, `moderator`, `admin`) | RBAC (Day 5) |
| `permissions` | `id`, `code` UNIQUE (`post:create`, `post:delete:any`, `comment:delete:any`, `user:manage`) | |
| `role_permissions` | **composite PK** (`role_id`, `permission_id`) | M:N junction |
| `user_roles` | **composite PK** (`user_id`, `role_id`) | M:N junction |
| `refresh_tokens` | `id`, `user_id` FK, `token_hash`, `expires_at`, `revoked_at`, `replaced_by` | Rotation + logout/revocation |
| `posts` | `id`, `author_id` FK → users, `title`, `slug` UNIQUE, `excerpt`, `content` (markdown), `cover_image_key`, `status` (`draft`/`published`), `published_at`, `ai_summary`, audit fields, **`deleted_at`** | Soft delete; `author_id` = the "tenant key" |
| `tags` / `post_tags` | `post_tags` composite PK (`post_id`, `tag_id`) | Filtering by tag |
| `comments` | `id`, `post_id` FK, `author_id` FK, `body`, audit fields, `deleted_at` | 1:N from posts |
| `likes` | **composite PK** (`user_id`, `post_id`), `created_at` | PK itself enforces "one like per user", so no race conditions |
| `audit_logs` | `id`, `actor_id`, `action`, `entity_type`, `entity_id`, `metadata` JSONB, `ip`, `created_at` | Day 5 audit logs; append-only |

**Audit fields mixin** on every entity: `created_at`, `updated_at`, `created_by`, `updated_by`.

### Relationships & cardinality
- User 1 ─── N Posts, User 1 ─── N Comments, Post 1 ─── N Comments
- User N ─── M Posts via `likes`; Post N ─── M Tags; User N ─── M Roles; Role N ─── M Permissions

### Indexes (Day 4)
| Index | Serves query |
|---|---|
| `posts (status, published_at DESC) WHERE deleted_at IS NULL` (partial) | Public feed |
| `posts (author_id, status)` (composite) | "My posts" dashboard |
| `posts.slug` UNIQUE | Read-by-slug |
| `comments (post_id, created_at)` | Comments under a post |
| `likes (post_id)` | Like counts (PK already covers `user_id` lookups) |
| GIN on `to_tsvector(title ‖ content)` *(stretch)* | Search |

We'll run `EXPLAIN ANALYZE` before/after adding these with ~10k seeded posts, and paste results into `docs/database.md`.

### Multi-tenancy: an honest note
A blog platform isn't truly multi-tenant (no orgs). Here the **tenant = the author**: every write is scoped by `author_id`, and "my drafts" queries always filter `WHERE author_id = :current_user`. We implement *tenant context* as a dependency that injects the current user into services, so no query can forget the scope. That covers the Day 3/5 concepts without inventing fake organizations. (Stretch: add `workspaces` if you want real tenants.)

---

## 4. API Contract (v1)

Base: `/api/v1`. Errors follow **RFC 9457 Problem Details**:
```json
{ "type": "about:blank", "title": "Forbidden", "status": 403,
  "detail": "You can only edit your own posts", "instance": "/api/v1/posts/abc", "request_id": "..." }
```
List responses: `{ "items": [...], "total": 123, "limit": 20, "offset": 0 }`

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register` | — | Create account → 201 |
| POST | `/auth/login` | — | Returns access token; sets httpOnly refresh cookie |
| POST | `/auth/refresh` | cookie | Rotate refresh token, new access token |
| POST | `/auth/logout` | ✓ | Revoke refresh token → 204 |
| GET | `/users/me` | ✓ | Current profile (+ roles/permissions for UI) |
| PATCH | `/users/me` | ✓ | Update profile |
| GET | `/users/{username}` | — | Public profile + their published posts |
| GET | `/posts` | optional | Public feed. Query: `limit, offset, sort=-published_at\|-likes, tag, author, q` |
| GET | `/posts/{slug}` | optional | Read post (includes `like_count`, `comment_count`, `liked_by_me`) |
| GET | `/me/posts` | ✓ | My posts incl. drafts, `status` filter |
| POST | `/posts` | ✓ | Create (draft by default) → 201 |
| PATCH | `/posts/{id}` | owner | Update |
| POST | `/posts/{id}/publish` / `/unpublish` | owner | State transition |
| DELETE | `/posts/{id}` | owner or `post:delete:any` | Soft delete → 204 |
| POST | `/posts/{id}/cover` | owner | multipart upload (jpeg/png/webp, ≤ 2 MB) |
| PUT | `/posts/{id}/like` | ✓ | Idempotent like → 204 |
| DELETE | `/posts/{id}/like` | ✓ | Unlike → 204 |
| GET | `/posts/{id}/comments` | — | Paginated |
| POST | `/posts/{id}/comments` | ✓ | Add comment → 201 |
| PATCH/DELETE | `/comments/{id}` | owner / `comment:delete:any` | Edit / soft delete |
| GET | `/integrations/cover-search?q=` | ✓ | Unsplash image search proxy (rate-limited, cached) |
| GET | `/me/posts/export?format=csv` | ✓ | Streamed CSV download of my posts + stats |
| GET | `/admin/audit-logs` | `audit:read` | Admin only |
| GET | `/health/live`, `/health/ready`, `/metrics` | — | Ops |

Status codes used: 200, 201, 204, 400, 401, 403, 404, 409 (duplicate email/slug), 413 (file too large), 415 (bad file type), 422 (validation), 429 (rate limit), 500, 503.

**Design choice worth noting:** likes use `PUT`/`DELETE` on a sub-resource. Liking twice is idempotent, which is a REST principle in practice.

---

## 5. Git & GitHub Workflow (Day 1), plus how your learning shows up in the repo

### Strategy: GitHub Flow + Conventional Commits
- `main` is always deployable and **protected** (require PR + passing CI).
- One branch per phase: `feat/p03-auth`, `feat/p05-likes-comments`, `chore/p11-docker-ci`...
- Commit messages: `type(scope): summary`, e.g.
  - `feat(auth): add JWT access and rotating refresh tokens`
  - `fix(posts): prevent editing posts owned by other users`
  - `perf(db): add composite index on posts(author_id, status)`
  - `docs(learning): day 3 log, auth vs authorization`
- Each phase ends with a **PR** (even solo; you review your own diff, which is great practice) using a template that has a **"🎓 Bootcamp concepts applied"** section.

### Making day-wise learning visible (what you asked for)
1. **Learning log per day** `docs/learning-log/day-0N.md`: topics covered → *where exactly it's used in this repo* (file links) → what was learned but *not applicable* and why (e.g. webhooks, DNS). Reviewers love the honesty of the "not applied" part.
2. **Git tags per day**: `git tag -a day-1 -m "Day 1: Engineering foundations"` after merging that day's PRs → the GitHub "Releases" page becomes a day-by-day timeline of the project.
3. **PR descriptions** list concepts applied, with a checkbox per Day topic.
4. **README section "Bootcamp Learning Map"** is a table: Day → Topics → Implemented in (links).

This fits your point: not every day's topics apply fully, but the log and tags show you *understood* each one and made deliberate decisions.

---

## 6. Phase-by-Phase Build Plan

Each phase shows: **Build**, **Concepts used** (short briefs), **Commits/PR**, **Done when**.

---

### Phase 0: Machine & Repo Setup  *(Day 1)*
**Build**
- Install (terminal): Xcode Command Line Tools → Homebrew → `git`, `gh`, `uv`, `fnm` + Node LTS, `colima` + `docker` + `docker-compose` + `docker-buildx`. VS Code extensions (Python, Ruff, Tailwind, ESLint, Docker). Optional downloads: Bruno, DBeaver Community.
- `git config` (name, email, `init.defaultBranch main`), SSH key → GitHub, `gh auth login`.
- Create **public** repo `nebula`, clone, add `.gitignore`, `LICENSE` (MIT), skeleton `README.md`, `.editorconfig`, `.env.example`, PR template, branch protection on `main`.
- Copy this plan into `docs/`.

**Concepts**
- **SDLC**: we follow plan → design (this doc, ADRs) → build → test (CI) → deploy (Docker) → maintain (logs/metrics). The phases below *are* the SDLC.
- **Terminal / package managers**: brew (system), uv (Python deps + venv + lockfile), npm (JS). Lockfiles make builds reproducible.
- **Environment variables**: config lives in `.env` (git-ignored); `.env.example` documents every variable with safe defaults. Source code never contains secrets.
- **Git/branching/commits/PRs**: see Section 5.

**Commits**: `chore: initialize repository`, `docs: add build plan and PR template`
**Done when**: public repo exists, `main` protected, you can open a PR.

---

### Phase 1: Backend Skeleton, Config, Logging, Errors  *(Day 1 → Day 2)*
**Build**
- `uv init backend`, add fastapi, uvicorn, pydantic-settings, ruff, mypy, pytest.
- App factory `create_app()`, `/api/v1` router, `GET /health/live`.
- `core/config.py` (typed `Settings` from env), `core/logging.py` (JSON logs), **RequestID middleware**, global exception handlers → Problem Details format.
- `pre-commit` with ruff + mypy; `Makefile` targets: `make dev`, `make test`, `make lint`.

**Concepts**
- **Client-server / frontend vs backend**: the backend is a stateless JSON API; any client (React, curl, mobile) talks to it over HTTP.
- **HTTP basics & request/response lifecycle**: request → uvicorn (ASGI server) → middleware chain → router → dependency resolution → handler → response serialization → middleware (reverse) → client. We'll document this path in `architecture.md`.
- **Ports**: API on 8000, frontend 5173, Postgres 5432, Redis 6379. **DNS** is `localhost` → 127.0.0.1 locally; in Docker Compose, service names (`db`, `redis`) are resolved by Docker's internal DNS, a good concrete example of DNS.
- **Dependency injection (prereq)**: FastAPI `Depends()` provides settings, DB sessions and the current user to handlers, which makes testing easy (override deps).
- **Exception handling & logging (prereq)**: custom `AppError` hierarchy (`NotFound`, `Forbidden`, `Conflict`) mapped to status codes in one place.

**Commits**: `feat(api): app factory and health endpoint`, `feat(core): typed settings from environment`, `feat(core): structured logging with request ids`, `feat(core): problem-details error handling`, `chore: pre-commit, ruff, mypy`
**Tag**: `day-1`  **Done when**: `make dev` serves `/docs`; `make test` green.

---

### Phase 2: Database Schema, Models, Migrations  *(Day 2 + DB prerequisites)*
**Build**
- Postgres + Redis via a minimal `docker-compose.yml` (just DBs for now).
- SQLAlchemy async engine/session, `Base` + `TimestampMixin`, `SoftDeleteMixin`.
- Models from Section 3; Alembic initial migration; `scripts/seed.py` (Faker, users/posts/comments/likes; `--count 10000` for perf testing later).

**Concepts**
- **PK/FK, constraints**: FKs with `ON DELETE` rules; `CHECK (status IN (...))`; `UNIQUE(email)`.
- **Normalization**: tags in their own table (not a comma string); counts computed, not duplicated (discuss denormalized counters as a trade-off).
- **Composite keys**: `likes(user_id, post_id)` makes duplicate likes *impossible at DB level*, not just in code.
- **Soft deletes & audit fields**: `deleted_at` keeps history and enables undo; queries must filter it (we centralize this in repositories).
- **Migrations**: every schema change is a versioned, reviewable Alembic file. Never edit the DB by hand.
- **Transactions**: one DB session per request; commit on success, rollback on exception.

**Commits**: `feat(db): async session and base mixins`, `feat(models): users, posts, comments, likes, tags, rbac`, `feat(db): initial alembic migration`, `feat(scripts): seed data generator`
**Done when**: `alembic upgrade head` builds the schema; ERD in `docs/database.md`.

---

### Phase 3: Authentication  *(Day 3)*
**Build**
- Register / login / refresh / logout / me.
- Argon2id hashing; **short-lived access JWT (15 min)** in `Authorization: Bearer`; **refresh token (7 days)** as `httpOnly; Secure; SameSite=Strict` cookie scoped to `/api/v1/auth`, stored **hashed** in DB, **rotated** on each use (reuse detection → revoke family).
- Deps: `get_current_user` (401 if missing/invalid) and `get_optional_user` (for public endpoints that personalize, e.g. `liked_by_me`).
- CORS: explicit allowed origins from env, `allow_credentials=True`.
- Login rate limit (e.g. 5/min/IP).

**Concepts**
- **Password hashing**: one-way + salted + deliberately slow (Argon2id) so DB leaks don't leak passwords.
- **Sessions vs JWT**: sessions = server stores state; JWT = signed, self-contained, stateless. We use a hybrid: stateless access token + revocable, stateful refresh token (a common production pattern, and it fixes JWT's "can't log out" weakness).
- **Authentication vs authorization**: *who are you* (401) vs *what are you allowed to do* (403).
- **Secure secrets**: `JWT_SECRET` from env, min length validated at startup, never committed; rotate by env change.
- **CORS**: the browser blocks cross-origin calls unless the API allows the origin. Credentials + wildcard origin is forbidden, so we list origins explicitly.

**Tests**: wrong password, expired token, tampered token, refresh reuse, duplicate email → 409.
**Commits**: `feat(auth): password hashing and user registration`, `feat(auth): jwt access tokens and current-user dependency`, `feat(auth): rotating refresh tokens with revocation`, `feat(core): cors configuration`, `test(auth): ...`
**Tag**: `day-3`

---

### Phase 4: Posts, Public Browsing & Ownership  *(Day 2 REST + Day 3 ownership)*
**Build**
- CRUD + publish/unpublish, slug generation (unique, collision-safe), markdown content.
- Public feed with **pagination** (limit ≤ 100), **filtering** (tag, author, `q`), **sorting** (whitelisted fields only).
- `/me/posts` shows drafts (tenant-scoped). Soft delete.
- Ownership check in the **service** layer: `if post.author_id != user.id and not user.can("post:delete:any"): raise Forbidden`.
- Drafts/deleted posts return **404** (not 403) to non-owners, so their existence isn't leaked.

**Concepts**
- **REST resources / URI design**: nouns (`/posts`), plural, hierarchy for ownership (`/posts/{id}/comments`), actions as state transitions (`/publish`).
- **HTTP methods**: `GET` safe, `PUT/DELETE` idempotent, `PATCH` partial update, `POST` create.
- **Path vs query params**: path identifies *which* resource; query refines *how* to list it.
- **Versioning**: `/api/v1`, so breaking changes go to `/v2` without breaking clients.
- **Resource ownership**: enforced server-side always; the UI hiding a button is not security.

**Commits**: `feat(posts): create, update and soft-delete with ownership rules`, `feat(posts): public feed with pagination, filtering and sorting`, `feat(posts): publish workflow and slugs`, `test(posts): ownership and visibility`
**Tag**: `day-2` (move/adjust tags to match when you actually finish)

---

### Phase 5: Likes & Comments  *(core requirement)*
**Build**
- `PUT/DELETE /posts/{id}/like` (idempotent; `INSERT ... ON CONFLICT DO NOTHING`).
- Comments CRUD, soft delete, owner or moderator can delete.
- Post read includes `like_count`, `comment_count`, `liked_by_me` computed in **one query** (aggregation + subquery / `EXISTS`).
- Rule decision to document: can authors like their own post? (Assignment says "*other* logged-in users", so block self-like → 403/409; note it in ADR.)

**Concepts**
- **Aggregations & subqueries (prereq)**: `COUNT(*)` grouped per post; correlated `EXISTS` for `liked_by_me`.
- **Joins**: author info joined into comment lists.
- **Idempotency**: the same request twice → same state.

**Commits**: `feat(likes): idempotent like/unlike`, `feat(comments): comment crud with moderation rights`, `feat(posts): engagement counts in feed`
**Done when**: the whole backend assignment is functionally complete ✅ *(this is your safety checkpoint)*

---

### Phase 6: Frontend (thin but polished)  *(Day 1 FE/BE communication, Day 5 permission-based UI)*
**Build**
- Vite + React + TS + Tailwind + TanStack Query + React Router.
- Pages: Feed, Post detail (like button, comments), Login/Register, My Dashboard (drafts/published), Editor (markdown + preview + cover upload), Profile.
- API client with automatic refresh-on-401; access token kept **in memory** (not localStorage → XSS-safer).
- Permission-based UI: edit/delete buttons only for owner/moderator, using `/users/me` permissions.
- Optional: generate TS types from OpenAPI (`openapi-typescript`), so the API contract is enforced at compile time.

**Concepts**
- **Frontend-backend communication**: `fetch` + JSON + Bearer header + credentials for cookie; CORS in action; loading/error states from Problem Details.
- **Permission-based UI**: UX convenience layered over server-side enforcement.

**Commits**: `feat(web): scaffold vite react app`, `feat(web): auth flow with silent refresh`, `feat(web): feed and post detail`, `feat(web): editor and dashboard`, `feat(web): likes and comments`

---

### Phase 7: File Uploads & Exports  *(Day 4, part 1)*
**Build**
- Cover image upload: `multipart/form-data`, **max 2 MB**, allow jpeg/png/webp verified by **magic bytes** (not just extension/Content-Type), Pillow re-encode + resize (strips EXIF/malicious payloads).
- Filenames: `covers/{uuid}.webp`, never user-supplied names (path traversal!).
- `StorageBackend` interface → `LocalStorage` now; `S3Storage` (or MinIO in compose) as stretch, switchable by env.
- Export "my posts" as **CSV** (`StreamingResponse`, row-by-row generator). PDF dropped for lightness (noted in learning log).
- Secure downloads: exports only for the authenticated owner; `Content-Disposition: attachment`.

**Concepts**
- **Streaming & buffers**: read upload in chunks and abort once > limit (don't load 1 GB into RAM); stream CSV out.
- **Temporary files**: `tempfile.NamedTemporaryFile` + `BackgroundTask` cleanup.
- **Local vs object storage**: local is simple but doesn't scale across containers; object storage (S3) does. The interface lets you swap.

**Commits**: `feat(uploads): validated cover image upload`, `feat(storage): pluggable storage backend`, `feat(export): streamed csv and pdf export of user posts`

---

### Phase 8: Performance & API Optimization  *(Day 4, part 2)*
**Build**
- Seed 10k posts → measure `GET /posts` → fix:
  - **N+1**: demonstrate the problem (log SQL count per request), fix with `selectinload(author)` and aggregate subqueries.
  - **Indexes** from Section 3; capture `EXPLAIN ANALYZE` before/after (Seq Scan → Index Scan) in `docs/database.md`.
  - **Payload reduction**: feed returns `PostSummary` (excerpt, no full content); full content only on detail.
  - **Caching**: Redis cache for public feed pages & post detail (short TTL + invalidate on write); `ETag`/`Cache-Control` headers for public GETs.
  - **Rate limiting**: `slowapi` backed by Redis (global + stricter on auth, comments, AI endpoint) → 429 with `Retry-After`.
  - **Compression**: `GZipMiddleware` for responses > 1 KB.
  - **Batching**: bulk like/comment counts fetched for a whole page in one query (not per post).

**Concepts**: eager vs lazy loading, composite & partial indexes, query plans, cache invalidation ("the hard problem"), rate limit algorithms (fixed window vs token bucket).

**Commits**: `perf(posts): eliminate n+1 in feed with selectinload`, `perf(db): add feed and dashboard indexes`, `perf(api): redis caching for public reads`, `feat(api): rate limiting`, `perf(api): gzip compression`, `docs(db): explain analyze before/after`
**Tag**: `day-4`

---

### Phase 9: Third-Party API Integration  *(Day 2, part 3)*
**Build**
- `integrations/unsplash.py`: backend proxy `GET /api/v1/integrations/cover-search?q=space` → Unsplash search (key stays server-side, never in the browser).
- Raw `httpx.AsyncClient` with **timeout** (5s), **retries with exponential backoff + jitter** for 5xx/network errors only (`tenacity`), honour `X-Ratelimit-Remaining` → our own 429 when exhausted, short Redis cache per query to save quota.
- **Data mapping**: Unsplash JSON → internal `CoverImage {url, thumb, author_name, author_link}` schema (vendor shape never leaks; attribution shown per Unsplash guidelines).
- No key configured → automatic fallback to Picsum (no key needed), so the app always works on a fresh clone.
- Tests mock HTTP with `respx` (no real calls in CI).
- *Stretch:* "Sign in with GitHub" (OAuth2 authorization-code flow, free GitHub OAuth App).

**Concepts**: API keys & **secrets** (env only, never logged), SDK vs raw HTTP (we pick raw HTTP to learn the mechanics; ADR), timeouts, retries, rate limits, request/response mapping, graceful degradation. **OAuth2**: stretch above, otherwise explained in learning log. **Webhooks**: documented as not applicable (where they'd fit: notify Discord/Slack on publish).

**Commits**: `feat(integrations): unsplash client with timeout, retries and rate-limit handling`, `feat(integrations): picsum fallback when no api key`, `feat(web): cover image picker`

---

### Phase 10: RBAC & Audit Logs  *(Day 5, part 1)*
**Build**
- Seed roles/permissions (migration data): `user` (default), `moderator` (delete any comment/post), `admin` (manage users, read audit logs).
- `require_permission("comment:delete:any")` dependency (= **guard**); ownership OR permission checks in services.
- Admin endpoints: list users, assign role, deactivate user.
- `audit_logs` written in the service layer for: login, failed login, post publish/delete, role change, moderation deletes.

**Concepts**: roles vs permissions, role-permission mapping, guards, **least privilege** (new users get only `user`), tenant-aware authorization (owner scoping + global moderator rights), audit trail.

**Commits**: `feat(rbac): roles, permissions and seed data`, `feat(rbac): permission guard dependency`, `feat(admin): user and role management`, `feat(audit): audit log for sensitive actions`

---

### Phase 11: Docker, CI/CD, Observability, Backups  *(Day 5, part 2)*
**Build**
- **Backend Dockerfile (multi-stage)**: builder stage installs deps with uv → slim runtime stage, non-root user, `HEALTHCHECK`.
- **Frontend Dockerfile**: node build stage → nginx static stage.
- **docker-compose.yml**: `api`, `web`, `db`, `redis`, (`migrate` one-shot job), healthcheck-based `depends_on`, named volumes. `docker compose up` = whole app.
- **CI (GitHub Actions)**: on PR → ruff, mypy, pytest (Postgres service), frontend lint/build, docker build. Badge in README.
- **CD (conceptual / optional)**: build & push image to GHCR on tag.
- **Observability**: JSON logs with `request_id`, `user_id`, latency; `/health/ready` checks DB + Redis; Prometheus `/metrics` (request count, latency histograms); unhandled exceptions logged with full context + optional GlitchTip DSN (free, self-hostable, Sentry-SDK compatible).
- **Backups**: `scripts/backup_db.sh` (`pg_dump` timestamped, keep last N) + `restore_db.sh`; `make backup`.

**Concepts**: build vs runtime (build-time deps don't ship; runtime config via env), image size, health (liveness vs readiness), logs vs metrics vs traces, CI vs CD.

**Commits**: `build(docker): multi-stage images for api and web`, `build(compose): full local stack`, `ci: lint, type-check, test and build pipeline`, `feat(obs): readiness checks and prometheus metrics`, `chore(ops): database backup and restore scripts`
**Tag**: `day-5`

---

### Phase 12: Documentation, README, Demo  *(end of week)*
**README.md** structure: title + badges → one-line pitch → screenshot/GIF → features → tech stack → architecture diagram → **Quickstart (Docker, 3 commands)** → local dev without Docker → env vars table → running tests → API overview (link to Swagger + `docs/api.md`) → project structure → **Bootcamp Learning Map** → roadmap/stretch → license.

**docs/**: `architecture.md` (diagrams incl. request lifecycle & auth sequence in Mermaid), `api.md` (contracts, examples, error format), `database.md` (ERD, indexes, EXPLAIN), `usage.md` (end-user guide with screenshots), `adr/0001..` (JWT hybrid, Postgres, layered arch, soft delete, self-like rule), `learning-log/day-01..05.md`.

**Tag**: `v1.0.0` release.

---

## 7. Suggested Timeline

| Day | Phases | Evening checkpoint |
|---|---|---|
| Day 1 | P0, P1 | Repo public, CI stub, API skeleton running |
| Day 2 | P2, P4 (start) | Schema migrated, post endpoints (no auth yet) |
| Day 3 | P3, finish P4, P5 | **Core backend complete** ✅ |
| Day 4 | P6 (frontend core), P7, P8 | Usable UI; uploads; perf numbers |
| Day 5 | P10, P11, P9 | `docker compose up` runs everything; CI green |
| Weekend / Day 6 | P6 polish, P12, demo recording | Submit |

If you're behind, drop in this order: GitHub OAuth stretch → Unsplash (keep Picsum) → Prometheus → Redis cache → admin endpoints. Never drop tests for auth/ownership.

---

## 8. 2-Minute Demo Script

1. (0:00) `git clone` → `cp .env.example .env` → `docker compose up`, show healthy containers. *(local execution)*
2. (0:20) Logged-out: browse feed, filter by tag, open post: can read, but like/comment prompts login.
3. (0:40) Register Alice → create draft with cover image → publish. Show draft invisible to others.
4. (1:05) Log in as Bob → like & comment on Alice's post; try to edit Alice's post → blocked (show 403 in Swagger).
5. (1:25) Moderator deletes a comment → audit log entry.
6. (1:40) Quick flash: Swagger `/docs`, CI green checks, `docs/` folder, learning log.
7. (1:55) Close.

---

## 8b. Security Plan (repo is PUBLIC, so security is non-negotiable)

### Repository level: nothing sensitive ever reaches GitHub
| Control | How |
|---|---|
| Secrets never committed | `.env` git-ignored from commit #1; only `.env.example` with placeholders; settings fail fast if secrets are default/weak in non-dev envs |
| Local secret scan | `gitleaks` in **pre-commit** (blocks the commit) |
| CI secret scan | `gitleaks` job on every PR (full history) |
| GitHub push protection | Secret scanning + push protection ON (free for public repos) |
| Dependency vulnerabilities | Dependabot alerts + security updates; `pip-audit` + `npm audit` in CI |
| Code scanning | GitHub **CodeQL** (free for public repos) for Python + TypeScript |
| Branch protection | `main`: PR required, CI must pass, no force-push, no deletion |
| Author privacy | Commits use `mr-laboratory` noreply email; enable "Block command line pushes that expose my email" |
| Account | 2FA enabled on GitHub |
| Data in repo | Seed data is 100% fake (Faker); no real names/emails in fixtures, screenshots or docs; DB dumps/uploads git-ignored |
| Policy | `SECURITY.md` (how to report vulnerabilities) |

### Application level: user data stays private
| Risk | Control |
|---|---|
| Password theft | Argon2id hashing; passwords never logged or returned; min length 8 + common-password check |
| Leaking user fields | Response schemas are **explicit whitelists**; `password_hash` never serialized; **email is private** (only visible to the user themselves via `/users/me`); public profiles show username, display name, bio only |
| Account enumeration | Login returns the same generic "Invalid credentials" for unknown email or wrong password; register conflict message is generic |
| Brute force | Rate limit on login/register (per IP + per account) |
| Token theft | Access JWT 15 min in memory only (not localStorage); refresh token in `httpOnly; Secure; SameSite=Strict` cookie, stored **hashed**, rotated, reuse → revoke all |
| Seeing others' drafts | Drafts & soft-deleted content return **404** to non-owners |
| Editing others' content | Ownership checked in the service layer + tests for every write endpoint |
| XSS via blog content | Markdown rendered with sanitization (`rehype-sanitize`); strict **Content-Security-Policy** |
| SQL injection | ORM parameterized queries only; sort/filter fields whitelisted |
| Clickjacking / sniffing | Security headers: CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, HSTS (prod) |
| CORS abuse | Explicit origin allow-list from env, never `*` with credentials |
| Info leakage in errors | Problem-details errors, no stack traces or SQL to clients; `request_id` for correlation |
| PII in logs | Log redaction filter: `Authorization`, cookies, `password`, tokens removed; emails masked |
| Infra exposure | Containers run as non-root; Postgres/Redis bound to `127.0.0.1` only; DB password from env |
| Oversized/malicious input | Pydantic length limits on all fields; request body size limit |

---

## 9. Production-Grade Checklist

- [ ] No secrets in git (`.env` ignored; `gitleaks` in pre-commit optional)
- [ ] All inputs validated (Pydantic lengths, enums, email)
- [ ] Ownership enforced server-side + tests prove it
- [ ] Consistent error format, no stack traces to clients
- [ ] Passwords Argon2id; tokens short-lived; refresh revocable
- [ ] CORS explicit; security headers (HSTS, X-Content-Type-Options)
- [ ] Pagination capped; sort fields whitelisted (no SQL injection via `sort`)
- [ ] Indexes justified with EXPLAIN
- [ ] Rate limits on auth & write endpoints
- [ ] Structured logs with request IDs; health checks; metrics
- [ ] Tests ≥ ~80% on services; CI required on `main`
- [ ] One-command startup; README tested on a clean clone
