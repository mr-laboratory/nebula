# Database

PostgreSQL 16, accessed through SQLAlchemy 2 (async, asyncpg driver). Schema changes are managed exclusively by Alembic migrations in [`backend/migrations/`](../backend/migrations/).

## Schema

```mermaid
erDiagram
    users {
        uuid id PK
        varchar email UK "lowercase"
        varchar username UK "^[a-z0-9_]{3,30}$"
        varchar password_hash "private"
        varchar display_name
        varchar bio "nullable"
        bool is_active
        timestamptz created_at
        timestamptz updated_at
    }
    roles {
        smallint id PK
        varchar name UK "user | moderator"
    }
    permissions {
        smallint id PK
        varchar code UK "e.g. post:delete:any"
    }
    user_roles {
        uuid user_id PK,FK
        smallint role_id PK,FK
    }
    role_permissions {
        smallint role_id PK,FK
        smallint permission_id PK,FK
    }
    refresh_tokens {
        uuid id PK
        uuid user_id FK
        varchar token_hash UK "sha-256, never the raw token"
        timestamptz expires_at
        timestamptz revoked_at "nullable"
        uuid replaced_by_id FK "rotation chain"
        timestamptz created_at
    }
    posts {
        uuid id PK
        uuid author_id FK
        varchar title
        varchar slug UK
        varchar excerpt "nullable"
        text content "markdown"
        varchar cover_image_key "nullable"
        varchar status "draft | published"
        timestamptz published_at "required when published"
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at "soft delete"
    }
    tags {
        int id PK
        varchar name UK "^[a-z0-9-]{1,40}$"
    }
    post_tags {
        uuid post_id PK,FK
        int tag_id PK,FK
    }
    comments {
        uuid id PK
        uuid post_id FK
        uuid author_id FK
        text body "1-5000 chars"
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at "soft delete"
    }
    likes {
        uuid user_id PK,FK
        uuid post_id PK,FK
        timestamptz created_at
    }

    users ||--o{ posts : writes
    users ||--o{ comments : writes
    users ||--o{ likes : gives
    users ||--o{ refresh_tokens : owns
    users ||--o{ user_roles : has
    roles ||--o{ user_roles : ""
    roles ||--o{ role_permissions : grants
    permissions ||--o{ role_permissions : ""
    posts ||--o{ comments : has
    posts ||--o{ likes : receives
    posts ||--o{ post_tags : ""
    tags ||--o{ post_tags : ""
    refresh_tokens |o--o| refresh_tokens : "replaced by"
```

## Integrity rules enforced by the database

The API validates input too, but these rules hold even if application code has a bug.

| Rule | Constraint |
|---|---|
| One account per email / username | `uq_users_email`, `uq_users_username` |
| Emails stored lowercase (case-insensitive uniqueness) | `ck_users_email_lowercase` |
| URL-safe usernames and tag names | `ck_users_username_format`, `ck_tags_name_format` |
| Post status is `draft` or `published` | `ck_posts_post_status` |
| A published post always has a publish date | `ck_posts_published_has_date` |
| Unique post URLs | `uq_posts_slug` |
| Comments are 1–5000 characters | `ck_comments_body_length` |
| A user can like a post only once | `pk_likes` (composite key) |
| Refresh tokens are unique and stored hashed | `uq_refresh_tokens_token_hash` |

## Deletion behaviour

```mermaid
flowchart LR
    U[DELETE user] -->|CASCADE| P[their posts] -->|CASCADE| X[comments · likes · post_tags on those posts]
    U -->|CASCADE| C[their comments · likes · roles · refresh tokens]
    T[refresh token deleted] -->|SET NULL| R[replaced_by_id on its predecessor]
```

Posts and comments are **soft-deleted** in normal use (`deleted_at` is set), so threads keep their history and accidental deletes are recoverable. The cascade rules apply to hard deletes, such as account removal.

## Design decisions

| Decision | Why |
|---|---|
| UUID primary keys for user-facing rows | IDs in URLs cannot be guessed or used to count records |
| Small integer keys for roles, permissions and tags | Tiny lookup tables; compact join tables |
| `timestamptz` everywhere | Unambiguous instants; the client formats for the user's time zone |
| Status as `varchar` + CHECK, not a native `ENUM` | Adding a status is a one-line migration; native enums are awkward to alter |
| Deterministic constraint names (naming convention) | Stable, readable migrations and clear error messages |
| Roles and permissions seeded by the initial migration | Reference data every environment needs; demo data lives in the seed script |
| No `created_by` / `updated_by` columns | `author_id` records ownership; moderator actions will be recorded in an audit log |
| Relationships load with `lazy="raise"` | Accidental N+1 queries fail loudly in tests instead of silently slowing the app |
| Performance indexes deferred | Added with `EXPLAIN ANALYZE` evidence once real queries exist |

## Working with the database

| Command | Purpose |
|---|---|
| `make db-up` / `make db-down` | Start / stop Postgres and Redis (data persists in a Docker volume) |
| `make migrate` | Apply pending migrations |
| `make migration m="add x"` | Autogenerate a migration from model changes; **always review it** |
| `make seed` | Reset and load deterministic demo data (refuses to run in production) |
| `make psql` | SQL shell on the local database |

Tests run against a separate `<POSTGRES_DB>_test` database. The suite migrates it once, runs each test inside a transaction that is rolled back, and verifies that models and migrations have not drifted apart (`alembic check`).
