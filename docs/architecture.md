# Architecture

How Nebula is structured and how each feature flows through it. For *why* each technology was chosen, see the [ADRs](adr/).

## 1. System overview

```mermaid
flowchart LR
    U([Browser]) -->|HTTPS| FE["<b>React SPA</b> · :5173<br/>UI, routing, forms<br/>access token in memory"]
    FE -->|"REST /api/v1<br/>Bearer token + refresh cookie"| API["<b>FastAPI</b> · :8000<br/>business rules, auth,<br/>single source of truth"]
    API --> PG[("<b>PostgreSQL</b><br/>users, posts, comments,<br/>likes, roles, tokens")]
    API --> RD[("<b>Redis</b><br/>rate limits, cache")]
    API --> FS[/"<b>Local storage</b><br/>cover images"/]
    API -.->|optional| UN["<b>Unsplash</b><br/>→ Picsum fallback"]
```

The API is **stateless**: session state lives in PostgreSQL and Redis, so instances can scale horizontally.

## 2. Backend layers

```mermaid
flowchart TB
    R["<b>Routes</b> — api/v1/routes<br/>parse HTTP · call service · return schema<br/>✗ no business rules, no SQL"]
    S["<b>Services</b> — services/<br/>ownership · drafts private · no self-likes<br/>✗ no HTTP details"]
    RP["<b>Repositories</b> — repositories/<br/>queries · eager loading · pagination<br/>✗ no authorization"]
    M["<b>Models</b> — models/<br/>tables · constraints · relations"]
    R --> S --> RP --> M
    SC["<b>Schemas</b><br/>whitelisted in/out fields"] -.-> R
    C["<b>Core</b><br/>config · logging · errors · security"] -.-> R & S & RP
    D["<b>Depends()</b><br/>settings · DB session · current user"] -.-> R
```

Dependencies point **downward only**.

## 3. Request lifecycle

```mermaid
flowchart LR
    C([Client]) --> ID["① Request ID<br/>X-Request-ID"] --> LOG["② Access log<br/>JSON, redacted"] --> CORS["③ CORS<br/>frontend origin only"] --> SH["④ Security headers<br/>CSP, nosniff, frame-deny"] --> RT["Route → Service → Repository"] --> DB[(PostgreSQL)]
    RT -->|success| OK["200/201/204<br/>response schema"]
    RT -->|domain error| PD["4xx Problem Details<br/>RFC 9457"]
    RT -->|unexpected| E5["500 generic message<br/>+ request_id only"]
    OK & PD & E5 --> C2([Client])
```

Error response shape:

```json
{ "type": "about:blank", "title": "Forbidden", "status": 403,
  "detail": "You can only edit your own posts",
  "instance": "/api/v1/posts/3f2c…", "request_id": "b1e4…" }
```

## 4. Feature flows

### 4.1 Browse and read (public)

```mermaid
sequenceDiagram
    participant V as Visitor
    participant API
    participant DB as PostgreSQL
    V->>API: GET /posts?limit=20&offset=0
    API->>DB: published · not deleted · newest first
    DB-->>API: posts + author + counts (one query)
    API-->>V: 200 {items, total, limit, offset}
    V->>API: GET /posts/{slug}
    alt published
        API-->>V: 200 post
    else draft/deleted and not owner
        API-->>V: 404 (existence never revealed)
    end
```

### 4.2 Sign-up, sign-in, refresh, sign-out

```mermaid
sequenceDiagram
    participant B as Browser
    participant API
    participant DB as PostgreSQL
    B->>API: POST /auth/register
    API->>DB: save Argon2id hash
    API-->>B: 201 public profile
    B->>API: POST /auth/login
    API->>DB: verify · store hashed refresh token
    API-->>B: access token (15 min) + httpOnly refresh cookie
    B->>API: POST /auth/refresh (cookie)
    API->>DB: revoke old · issue new (rotation)
    API-->>B: new access token + new cookie
    B->>API: POST /auth/logout
    API->>DB: revoke
    API-->>B: 204 · cookie cleared
```

### 4.3 Author manages own posts

```mermaid
stateDiagram-v2
    [*] --> Draft: POST /posts
    Draft --> Draft: PATCH /posts/{id}
    Draft --> Published: POST /publish
    Published --> Draft: POST /unpublish
    Published --> Published: PATCH /posts/{id}
    Draft --> Deleted: DELETE
    Published --> Deleted: DELETE
    Deleted --> [*]
    note right of Draft: visible to owner only
    note right of Published: visible to everyone
    note right of Deleted: soft delete (deleted_at)
```

```mermaid
flowchart LR
    Q["PATCH / DELETE /posts/{id}"] --> A{Owner?}
    A -->|yes| OK[✓ allowed]
    A -->|no| M{"Moderator?<br/>(delete only)"}
    M -->|yes| OK
    M -->|no| F[403 Forbidden]
```

### 4.4 Likes

```mermaid
flowchart LR
    L["PUT /posts/{id}/like"] --> S{Signed in?}
    S -->|no| U[401]
    S -->|yes| O{Own post?}
    O -->|yes| F[403]
    O -->|no| I["INSERT … ON CONFLICT DO NOTHING<br/>PK (user_id, post_id)"] --> N["204<br/>idempotent"]
```

### 4.5 Comments

```mermaid
flowchart LR
    R["GET /posts/{id}/comments"] --> P[200 paginated · public]
    C["POST /posts/{id}/comments"] --> S{Signed in +<br/>post published?}
    S -->|yes| K[201 created]
    S -->|no| X[401 / 404]
    E["PATCH / DELETE /comments/{id}"] --> W{"Comment author?<br/>Moderator (delete)?"}
    W -->|yes| Y[200 / 204]
    W -->|no| Z[403]
```

## 5. Data model

```mermaid
erDiagram
    USERS ||--o{ POSTS : writes
    USERS ||--o{ COMMENTS : writes
    POSTS ||--o{ COMMENTS : has
    USERS ||--o{ LIKES : gives
    POSTS ||--o{ LIKES : receives
    POSTS }o--o{ TAGS : "post_tags"
    USERS }o--o{ ROLES : "user_roles"
    ROLES }o--o{ PERMISSIONS : "role_permissions"
    USERS ||--o{ REFRESH_TOKENS : owns
```

Full schema, constraints and design decisions: [database.md](database.md).

## 6. Security layers

```mermaid
flowchart TB
    subgraph Browser
        B1["Access token in memory · refresh cookie httpOnly/Strict<br/>Sanitized Markdown · CSP"]
    end
    subgraph Edge["API edge"]
        B2["CORS allow-list · security headers · rate-limited auth"]
    end
    subgraph App["Application"]
        B3["Ownership & role checks · drafts → 404<br/>Whitelisted schemas · email private · generic login errors"]
    end
    subgraph Data
        B4["Argon2id passwords · hashed refresh tokens<br/>Secrets from env · redacted logs"]
    end
    subgraph Repo["Repository & CI"]
        B5["gitleaks · push protection · Dependabot · CodeQL · noreply commits"]
    end
    Browser --> Edge --> App --> Data
    Repo -.-> App
```

## 7. Observability

```mermaid
flowchart LR
    RQ[Request] --> LG["JSON log line<br/>request_id · path · status · ms"]
    RQ --> HD["X-Request-ID<br/>returned to client"]
    OPS([Ops / Docker]) --> LV["/health/live<br/>process up"]
    OPS --> RY["/health/ready<br/>DB + Redis reachable"]
    OPS --> MT["/metrics<br/>Prometheus"]
```

## 8. Implementation status

| Area | Status |
|---|---|
| Skeleton · config · logging · middleware · errors · liveness | ✅ Done (v0.1.0) |
| Database · migrations · readiness | ✅ Done (v0.2.0) |
| Authentication | Planned |
| Posts & public browsing | Planned |
| Likes & comments | Planned |
| Frontend | Planned |
| Indexes & query optimization | Planned |
| Roles (user / moderator) | Planned |
| Containers · CI · metrics | Planned |
