"""Post queries: visibility, filters, pagination, counts, and relations loaded without N+1."""

import uuid
from collections.abc import Sequence
from typing import Any, NamedTuple

from sqlalchemy import ColumnElement, Select, exists, false, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, defer, selectinload

from app.models import Comment, Like, Post, PostStatus, Tag, User
from app.schemas.post import MyPostFilters, PostFilters

PREVIEW_LENGTH = 280

# Everyone may see a post that is published and not deleted. The status is rendered inline
# (not as a bound parameter) so the planner can match the partial indexes on posts even when
# it reuses a generic plan for a prepared statement.
IS_PUBLIC: tuple[ColumnElement[bool], ...] = (
    Post.status == literal(PostStatus.PUBLISHED, Post.status.type, literal_execute=True),
    Post.deleted_at.is_(None),
)
# The author's excerpt, or else the start of the content, computed in SQL so the
# (possibly large) content never leaves the database for list pages.
PREVIEW = func.coalesce(Post.excerpt, func.left(Post.content, PREVIEW_LENGTH)).label("preview")
# Correlated subqueries: computed per row inside the same statement, so no extra round trips.
LIKE_COUNT = select(func.count()).select_from(Like).where(Like.post_id == Post.id).scalar_subquery()
COMMENT_COUNT = (
    select(func.count())
    .select_from(Comment)
    .where(Comment.post_id == Post.id, Comment.deleted_at.is_(None))
    .scalar_subquery()
)


class PostStats(NamedTuple):
    like_count: int
    comment_count: int
    liked: bool  # always False for anonymous viewers


class PostRow(NamedTuple):
    post: Post
    preview: str
    stats: PostStats


def _liked_by(viewer_id: uuid.UUID | None) -> ColumnElement[bool]:
    if viewer_id is None:
        return false()
    return exists().where(Like.post_id == Post.id, Like.user_id == viewer_id)


# List pages only show an author's name, so only those columns are read (email and
# password hash never leave the database for them); touching anything else raises.
AUTHOR_COLUMNS = (User.id, User.username, User.display_name)


def _with_relations(stmt: Select[Post]) -> Select[Post]:
    # Author: joined into the same query. Tags: one extra IN query for the whole page.
    return stmt.join(Post.author).options(contains_eager(Post.author), selectinload(Post.tags))


def _escape_like(term: str) -> str:
    # %, _ and \ are wildcards in LIKE; escape them so "100%" is searched literally.
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _page(
    session: AsyncSession,
    conditions: Sequence[ColumnElement[bool]],
    order_by: Sequence[ColumnElement[Any]],
    limit: int,
    offset: int,
    viewer_id: uuid.UUID | None,
) -> tuple[list[PostRow], int]:
    total = await session.scalar(select(func.count()).select_from(Post).where(*conditions))
    stmt = (
        select(Post, PREVIEW, LIKE_COUNT, COMMENT_COUNT, _liked_by(viewer_id))
        .join(Post.author)
        .options(
            contains_eager(Post.author).load_only(*AUTHOR_COLUMNS, raiseload=True),
            selectinload(Post.tags),
            defer(Post.content, raiseload=True),  # accidental access fails loudly
        )
        .where(*conditions)
        .order_by(*order_by)
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    return [
        PostRow(post, preview, PostStats(likes, comments, liked))
        for post, preview, likes, comments, liked in rows
    ], total or 0


async def list_public(
    session: AsyncSession, filters: PostFilters, viewer_id: uuid.UUID | None
) -> tuple[list[PostRow], int]:
    conditions = list(IS_PUBLIC)
    if filters.tag:
        conditions.append(Post.tags.any(Tag.name == filters.tag))
    if filters.author:
        conditions.append(Post.author.has(User.username == filters.author))
    if filters.q:
        pattern = f"%{_escape_like(filters.q)}%"
        conditions.append(
            or_(Post.title.ilike(pattern, escape="\\"), Post.excerpt.ilike(pattern, escape="\\"))
        )
    newest = filters.sort == "newest"
    order_by = (
        Post.published_at.desc() if newest else Post.published_at.asc(),
        Post.id.desc() if newest else Post.id.asc(),  # tie-breaker keeps pages stable
    )
    return await _page(session, conditions, order_by, filters.limit, filters.offset, viewer_id)


async def list_by_author(
    session: AsyncSession, author_id: uuid.UUID, filters: MyPostFilters
) -> tuple[list[PostRow], int]:
    conditions = [Post.author_id == author_id, Post.deleted_at.is_(None)]
    if filters.status:
        conditions.append(Post.status == filters.status)
    order_by = (Post.updated_at.desc(), Post.id.desc())
    return await _page(session, conditions, order_by, filters.limit, filters.offset, author_id)


async def get_by_slug(session: AsyncSession, slug: str) -> Post | None:
    """A non-deleted post with author and tags, any status (the caller decides visibility)."""
    stmt = _with_relations(select(Post)).where(Post.slug == slug, Post.deleted_at.is_(None))
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_id(session: AsyncSession, post_id: uuid.UUID) -> Post | None:
    stmt = (
        _with_relations(select(Post))
        .where(Post.id == post_id, Post.deleted_at.is_(None))
        .execution_options(populate_existing=True)  # always return fresh column values
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_stats(
    session: AsyncSession, post_id: uuid.UUID, viewer_id: uuid.UUID | None
) -> PostStats:
    stmt = select(LIKE_COUNT, COMMENT_COUNT, _liked_by(viewer_id)).where(Post.id == post_id)
    likes, comments, liked = (await session.execute(stmt)).one()
    return PostStats(likes, comments, liked)


async def slug_taken(session: AsyncSession, slug: str) -> bool:
    # Deleted posts keep their slug, so an old link can never point at a different post.
    return bool(await session.scalar(select(exists().where(Post.slug == slug))))


async def count_public_by_author(session: AsyncSession, author_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(Post).where(Post.author_id == author_id, *IS_PUBLIC)
    return await session.scalar(stmt) or 0
