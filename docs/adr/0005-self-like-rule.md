# ADR 0005 — Authors can't like their own posts

- **Status:** Accepted
- **Date:** 2026-09-26

## Context

The requirements say published posts can be liked by *other* signed-in users. Like counts appear on every feed card, so they should reflect readers' interest, not authors' self-promotion. The rule has to hold for the API, not just the UI.

## Decision

- `PUT /posts/{id}/like` returns **`403 Forbidden`** ("You can't like your own post.") when the caller is the author.
- The check lives in the like service, next to the other rules, and runs after visibility: a post the caller can't see is still `404`, and liking one's own **draft** is `409` (not published), so the error always describes the most relevant problem.
- Likes are idempotent: the primary key is `(user_id, post_id)` and the insert uses `ON CONFLICT DO NOTHING`, so repeated clicks never double-count.
- Unliking only needs the post to be readable, so a like can still be taken back after a post is unpublished.
- The UI hides the like button on the author's own posts (`canLike`), but that is a convenience; the API is the authority.

## Alternatives considered

- **Allow self-likes**: simpler, but contradicts the requirement and makes counts easy to inflate.
- **`409 Conflict`** for self-likes: `409` is used for state problems (a draft can't be liked); self-liking is about *who* is asking, which is what `403` means.
- **Silently ignore** the request: hides the rule from API clients and makes bugs harder to spot.

## Consequences

- Like counts mean "other people liked this".
- A client that ignores the rule gets a clear, documented error instead of a surprising count.
- The rule is covered by tests at the API level, together with the `404` and `409` cases.
