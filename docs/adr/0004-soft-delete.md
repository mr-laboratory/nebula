# ADR 0004 — Soft delete for posts and comments

- **Status:** Accepted
- **Date:** 2026-09-25

## Context

Posts and comments can be deleted by their authors, by the author of the post a comment is on, and by moderators. Deleting a comment from the middle of a thread would leave the replies around it without context. Moderators' deletions need to be traceable, and accidental deletes should be recoverable by an operator.

## Decision

- Posts and comments have a nullable `deleted_at` column. Deleting sets it; nothing is removed.
- Every query for visible content filters on `deleted_at IS NULL`, and the partial indexes used by the feed and the dashboard include that condition, so deleted rows cost nothing to skip.
- A deleted **post** behaves as if it never existed: `404` everywhere, including for its author.
- A deleted **comment** keeps its place in the thread as a placeholder, with its body and author removed from the response.
- Moderator deletions write an audit entry in the same transaction.
- Hard deletes are left to operators (for example, removing an account's data), and foreign-key cascades handle them. Accounts that performed audited actions are deactivated, not deleted, so the audit trail always names a real actor.

## Alternatives considered

- **Hard delete**: simplest, but breaks comment threads, loses evidence for moderation disputes, and can't be undone.
- **Archive table** (move deleted rows elsewhere): keeps the main tables small, but doubles the schema and complicates restores; unnecessary at this size.
- **Status value `deleted`** instead of a timestamp: works, but loses *when* it happened and mixes deletion with the draft/published lifecycle.

## Consequences

- Every read must remember the `deleted_at` filter. Repositories apply it in shared query builders, and tests cover deleted content for each endpoint.
- Deleted rows stay in the database until an operator removes them, which matters for personal-data requests: removal is an operator task today.
- Restoring content is a one-column update, done by an operator; there is no "undelete" button.
