"""Post rules: who can see and change a post, slug generation, and the publish workflow.

Visibility: published posts are public; drafts exist only for their author. Anyone else gets
404 for a draft (not 403), so its existence is never revealed.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.slugs import slugify, with_suffix
from app.models import Post, PostStatus, User
from app.repositories import posts as repo
from app.repositories import tags as tag_repo
from app.repositories.posts import PREVIEW_LENGTH, PostRow
from app.schemas.common import Page
from app.schemas.post import (
    MyPostFilters,
    PostCreate,
    PostDetail,
    PostFilters,
    PostSummary,
    PostUpdate,
)
from app.schemas.user import AuthorPublic
from app.services.permissions import POST_DELETE_ANY, has_permission

POST_NOT_FOUND = "Post not found."
NOT_YOUR_POST = "You can only change your own posts."
SLUG_ATTEMPTS = 5


# ─── Response mapping ─────────────────────────────────────


def _fields(post: Post, excerpt: str) -> dict[str, object]:
    return {
        "id": post.id,
        "slug": post.slug,
        "title": post.title,
        "excerpt": excerpt,
        "status": post.status,
        "author": AuthorPublic.model_validate(post.author),
        "tags": sorted(tag.name for tag in post.tags),
        "published_at": post.published_at,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }


def _summary(row: PostRow) -> PostSummary:
    post, preview = row
    return PostSummary.model_validate(_fields(post, preview))


def _detail(post: Post) -> PostDetail:
    excerpt = post.excerpt or post.content[:PREVIEW_LENGTH]  # same rule as the SQL preview
    return PostDetail.model_validate({**_fields(post, excerpt), "content": post.content})


# ─── Reading ──────────────────────────────────────────────


async def list_feed(session: AsyncSession, filters: PostFilters) -> Page[PostSummary]:
    rows, total = await repo.list_public(session, filters)
    return Page(
        items=[_summary(r) for r in rows], total=total, limit=filters.limit, offset=filters.offset
    )


async def list_mine(session: AsyncSession, user: User, filters: MyPostFilters) -> Page[PostSummary]:
    rows, total = await repo.list_by_author(session, user.id, filters)
    return Page(
        items=[_summary(r) for r in rows], total=total, limit=filters.limit, offset=filters.offset
    )


async def get_visible(session: AsyncSession, slug: str, viewer: User | None) -> PostDetail:
    post = await repo.get_by_slug(session, slug)
    if post is None:
        raise NotFoundError(POST_NOT_FOUND)
    is_owner = viewer is not None and viewer.id == post.author_id
    if post.status != PostStatus.PUBLISHED and not is_owner:
        raise NotFoundError(POST_NOT_FOUND)
    return _detail(post)


# ─── Ownership ────────────────────────────────────────────


async def _get_for_change(
    session: AsyncSession, post_id: uuid.UUID, user: User, override: str | None = None
) -> Post:
    """The post, if `user` owns it or holds the `override` permission. Otherwise 404/403."""
    post = await repo.get_by_id(session, post_id)
    if post is None:
        raise NotFoundError(POST_NOT_FOUND)
    if post.author_id == user.id:
        return post
    if override and await has_permission(session, user.id, override):
        return post
    if post.status != PostStatus.PUBLISHED:
        raise NotFoundError(POST_NOT_FOUND)  # someone else's draft: don't confirm it exists
    raise ForbiddenError(NOT_YOUR_POST)


async def _reload(session: AsyncSession, post_id: uuid.UUID) -> PostDetail:
    post = await repo.get_by_id(session, post_id)
    assert post is not None  # noqa: S101  (we just wrote it in this transaction)
    return _detail(post)


# ─── Slugs ────────────────────────────────────────────────


async def _save_with_unique_slug(session: AsyncSession, post: Post, base: str) -> None:
    """Flush `post` with a free slug: `base` if possible, else `base-<random>`.

    The pre-check handles the normal case. If another request takes the same slug between
    the check and our write, the UNIQUE constraint rejects it; only the savepoint is rolled
    back and we try another suffix.
    """
    candidate = base
    for _ in range(SLUG_ATTEMPTS):
        if not await repo.slug_taken(session, candidate):
            try:
                # begin_nested() flushes pending changes first, so the slug change must be
                # made inside the savepoint or a clash would roll back the whole transaction.
                async with session.begin_nested():
                    post.slug = candidate
                    session.add(post)
                    await session.flush()
                return
            except IntegrityError as exc:
                if "uq_posts_slug" not in str(exc.orig):
                    raise
        candidate = with_suffix(base)
    raise ConflictError("Could not create a unique link for this post. Please try again.")


# ─── Writing ──────────────────────────────────────────────


async def create(session: AsyncSession, author: User, data: PostCreate) -> PostDetail:
    post = Post(
        id=uuid.uuid4(),
        author_id=author.id,
        title=data.title,
        content=data.content,
        excerpt=data.excerpt or None,
        tags=await tag_repo.get_or_create(session, data.tags),
    )
    await _save_with_unique_slug(session, post, slugify(data.title))
    return await _reload(session, post.id)


async def update(
    session: AsyncSession, user: User, post_id: uuid.UUID, data: PostUpdate
) -> PostDetail:
    post = await _get_for_change(session, post_id, user)
    fields = data.model_fields_set
    new_base = slugify(data.title) if data.title is not None else None
    # Slugs are frozen once a post has been published, so shared links never break.
    retitle = new_base is not None and post.published_at is None and new_base != slugify(post.title)

    if data.title is not None:
        post.title = data.title
    if data.content is not None:
        post.content = data.content
    if "excerpt" in fields:
        post.excerpt = data.excerpt or None  # null or "" clears it: preview from content
    if data.tags is not None:
        post.tags = await tag_repo.get_or_create(session, data.tags)

    await session.flush()
    if retitle and new_base is not None:
        await _save_with_unique_slug(session, post, new_base)
    return await _reload(session, post.id)


async def set_status(
    session: AsyncSession, user: User, post_id: uuid.UUID, status: PostStatus
) -> PostDetail:
    """Publish or unpublish. Idempotent: setting the current status changes nothing."""
    post = await _get_for_change(session, post_id, user)
    if post.status != status:
        post.status = status
        if status == PostStatus.PUBLISHED and post.published_at is None:
            post.published_at = datetime.now(UTC)  # first publication; kept if unpublished
        await session.flush()
    return await _reload(session, post.id)


async def delete(session: AsyncSession, user: User, post_id: uuid.UUID) -> None:
    """Soft delete: the row stays (for moderation and undo later) but disappears everywhere."""
    post = await _get_for_change(session, post_id, user, override=POST_DELETE_ANY)
    post.deleted_at = datetime.now(UTC)
    await session.flush()
