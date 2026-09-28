# Day 4 — Performance, roles and audit

## Phase 7 — Indexes, query plans and HTTP caching

**Built:**
- a 10k-post seed (`make seed-large`) and a script that runs `EXPLAIN ANALYZE` on every hot read path (`make explain`);
- seven indexes chosen from those plans, in one migration (including pg_trgm for search);
- plan tests that fail if a query can no longer use its index;
- weak ETags with `304 Not Modified` for anonymous public reads, and gzip for large responses.

That adds 13 new tests, 145 in total. The slowest query went from 9.4 s to 18 ms; the feed's first page from 59 ms to 0.9 ms.

```mermaid
flowchart LR
    S["make seed-large<br/>10k posts · 100k likes"] --> B["make explain<br/>before: seq scans"]
    B --> I["Migration<br/>7 indexes + pg_trgm"]
    I --> A["make explain<br/>after: index scans"]
    A --> T["Plan tests in CI"]
```

| Query | Before | After |
|---|---:|---:|
| Feed, page 1 | 59 ms | 0.9 ms |
| Feed, offset 5000 | 9,377 ms | 18 ms |
| Search `?q=` | 75 ms | 2.0 ms |
| Dashboard | 57 ms | 0.4 ms |

Full table and index list: [database.md](../database.md#indexes-and-query-performance).

| Concept | What it means | Where it's applied |
|---|---|---|
| **Measure first** | `EXPLAIN (ANALYZE, BUFFERS)` runs the query and shows each step's real time and rows. Indexes are added only where a plan shows a scan that hurts | [`scripts/explain.py`](../../backend/scripts/explain.py) |
| **Seq scan vs index scan** | Without an index, PostgreSQL reads the whole table. A B-tree jumps straight to the matching rows, already in order, so `ORDER BY … LIMIT 20` stops after 20 | [`models/post.py`](../../backend/app/models/post.py) |
| **Composite index column order** | `likes` has PK `(user_id, post_id)`: great for "did I like it?", useless for "count this post's likes". An index is used left to right, so that needs its own `(post_id)` index | [`models/like.py`](../../backend/app/models/like.py) |
| **Partial index** | `WHERE status = 'published' AND deleted_at IS NULL` indexes only public posts: smaller, and exactly what the feed asks for | `ix_posts_feed` |
| **Generic plans vs partial indexes** | A prepared statement can be re-planned without its parameter values; then `status = $1` can't be matched to the index's `status = 'published'`. Rendering the constant inline fixes it | [`repositories/posts.py`](../../backend/app/repositories/posts.py) |
| **Index-only scan** | When the index holds every column a query needs, the table isn't read at all. The feed's `COUNT(*)` got this after dropping an unneeded join | same |
| **Trigram (pg_trgm) search** | `ILIKE '%term%'` can't use a B-tree (no fixed prefix). A GIN index of 3-letter fragments can | migration `bb601d208e54` |
| **Why a deep offset was slow** | The count subqueries run for every row *skipped* by `OFFSET`, not only the 20 returned. With indexes each is a quick lookup | [database.md](../database.md#indexes-and-query-performance) |
| **Conditional requests (ETag / 304)** | The response carries a fingerprint; the browser sends it back as `If-None-Match` and gets an empty `304` if nothing changed | [`core/middleware.py`](../../backend/app/core/middleware.py) |
| **Compression** | A 20-post page shrinks from 11.8 KB to 3.8 KB with gzip | same |

### What gets cached

```mermaid
flowchart TD
    R[GET request] --> A{"Authorization<br/>header?"}
    A -->|yes| N["no-store<br/>(may contain drafts, liked_by_me)"]
    A -->|no| P{"Public read path<br/>and 200?"}
    P -->|no| N2[no-store]
    P -->|yes| E["ETag + no-cache<br/>Vary: Authorization"]
    E --> M{"If-None-Match<br/>matches?"}
    M -->|yes| C["304 · empty body"]
    M -->|no| F[200 · full body]
```

**Security details worth remembering**

- Signed-in responses are `no-store`: they can hold drafts and per-user flags, so they never sit in a shared or on-disk cache.
- `Vary: Authorization` stops a shared cache from serving an anonymous copy to a signed-in reader.
- `/auth/*` responses are never gzipped. Compressing a secret next to attacker-influenced input can leak it through the response size (BREACH).
- List queries no longer load authors' email or password hash at all; the fewer places a secret travels, the fewer places it can leak.

**Decisions & trade-offs**

| Decision | Why | Cost |
|---|---|---|
| `no-cache` (revalidate) instead of `max-age` | Like counts and comments are never stale | One round trip per view, though a `304` has no body |
| ETag computed from the response body | Always correct, no version columns to maintain | The query still runs; it saves bandwidth, not database time |
| No Redis response cache | With indexes every read is 2 ms or less; a cache would add invalidation bugs for little gain | Revisit if traffic grows |
| Offset pagination kept | Simple, and page numbers work with the existing UI | Deep pages cost more; keyset pagination is the next step if needed |
| Plain `CREATE INDEX` | Fine at this size, inside a transaction | A large live table would need `CONCURRENTLY` |

**Lessons learned**

- Planner choices depend on statistics: on a 2,000-row test table the trigram index lost to a plain index scan, and at 10,000 rows it won. Plan tests need realistic data (and `ANALYZE`).
- A test is only useful if it can fail: reverting the inline status made the generic-plan test fail, and restoring it made it pass.
- The seed itself had an O(n²) loop (every user could like every post). Capping likes per post and inserting in bulk loads 10k posts in under 10 seconds.

## Phase 8 — Permissions, account management and an audit log

**Built:**
- an `admin` role with two new permissions, `user:manage` and `audit:read`;
- a `require_permission(code)` route guard;
- the `/admin` API: list accounts, grant and revoke roles, deactivate and reactivate;
- `make grant` / `make revoke` to create the first admin from the command line;
- an append-only `audit_logs` table recording moderator deletes, role changes and account status changes.

That adds 37 new tests, 182 in total. The biggest is a permission matrix: 4 viewers × 7 actions.

```mermaid
flowchart LR
    CLI["make grant<br/>u=alice role=admin"] --> A[alice: admin]
    A -->|"PUT /admin/users/bob/roles/moderator"| B[bob: moderator]
    B -->|"DELETE /posts/{id}"| D[Post removed]
    CLI & A & B -.->|same transaction| L[("audit_logs<br/>append-only")]
    A -->|"GET /admin/audit-logs"| L
```

| Concept | What it means | Where it's applied |
|---|---|---|
| **Roles vs permissions** | Code checks a permission (`user:manage`), never a role name. Roles are rows that bundle permissions, so changing what a role can do is data, not code | [`services/permissions.py`](../../backend/app/services/permissions.py) |
| **Least privilege** | New accounts get `user` only. Moderators can remove content but not manage people; admins manage people but can't remove content | migration `59ff4137ce49` |
| **Guard dependency** | `Depends(require_permission(...))` rejects the request before the handler runs: `401` anonymous, `403` without the permission | [`api/deps.py`](../../backend/app/api/deps.py) |
| **Permission matrix test** | Every viewer × every protected action, with the expected status in one table. A missing guard shows up as one wrong cell | [`test_admin.py`](../../backend/tests/test_admin.py) |
| **Lockout prevention** | No demoting or deactivating yourself; the last active admin can't be removed | [`services/admin.py`](../../backend/app/services/admin.py) |
| **Check-then-act race (TOCTOU)** | Two admins demoting each other at once could both pass the check. A row lock serialises the changes, and the permission is checked again after the lock | same |
| **Bootstrap trust** | The first admin can't come from the API. The CLI needs database access, which is already the highest trust level | [`scripts/roles.py`](../../backend/scripts/roles.py) |
| **Audit in the same transaction** | The action and its log entry commit or roll back together | [`services/audit.py`](../../backend/app/services/audit.py) |
| **Append-only in the database** | A trigger rejects `UPDATE` and `DELETE`, so even buggy code or a manual query can't rewrite history | same migration |
| **Deactivate, don't delete** | Blocks sign-in and revokes every refresh token. Access tokens stop working on the next request because each one re-checks `is_active`. Content and history stay, and it's reversible | same service |

### Who can do what

| Action | user | moderator | admin |
|---|:-:|:-:|:-:|
| Manage own posts and comments | ✓ | ✓ | ✓ |
| Delete anyone's post or comment | | ✓ | |
| List accounts, change roles, deactivate | | | ✓ |
| Read the audit log | | | ✓ |

**Security details worth remembering**

- The account listing is the only place, besides your own profile, where emails appear. It still never includes password hashes: the response schema lists its fields explicitly.
- Audit entries hold ids and role names only. Copying a deleted comment's text into the log would keep content that a moderator removed.
- An owner deleting their own post isn't audited, and neither is a post author removing a comment on their own post. Only uses of an override permission are.

**Decisions & trade-offs**

| Decision | Why | Cost |
|---|---|---|
| Admin has no moderation rights | Separate duties; an admin who needs them grants `moderator` to themselves, and that's audited | One extra step for small teams |
| One lock for all account changes | Simple, and the lockout rules can't race | Account changes run one at a time (they are rare) |
| Audit table blocks `UPDATE`/`DELETE` but not `TRUNCATE` | The seed reset and tests truncate everything | A database superuser can still wipe it; shipping logs off-box would cover that |
| No admin web page yet | The API, CLI and tests cover it; the UI can come later | Admin tasks use the API docs at `/docs` or the CLI |

**Lessons learned**

- Checking permissions rather than role names made the matrix test simple: the table *is* the specification.
- The "can't demote yourself" rule alone doesn't prevent a lockout. Two admins can demote each other at the same moment, so the lock and the re-check are what actually close the gap.
