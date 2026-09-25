"""Post queries: visibility rules, filters, pagination, and loading authors/tags without N+1."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, defer, selectinload

from app.models import Post, PostStatus, Tag, User
from app.schemas.post import MyPostFilters, PostFilters

PREVIEW_LENGTH = 280

# Everyone may see a post that is published and not deleted.
IS_PUBLIC: tuple[ColumnElement[bool], ...] = (
    Post.status == PostStatus.PUBLISHED,
    Post.deleted_at.is_(None),
)
# The author's excerpt, or else the start of the content, computed in SQL so the
# (possibly large) content never leaves the database for list pages.
PREVIEW = func.coalesce(Post.excerpt, func.left(Post.content, PREVIEW_LENGTH)).label("preview")

type PostRow = tuple[Post, str]


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
) -> tuple[list[PostRow], int]:
    total = await session.scalar(
        select(func.count()).select_from(Post).join(Post.author).where(*conditions)
    )
    stmt = (
        select(Post, PREVIEW)
        .join(Post.author)
        .options(
            contains_eager(Post.author),
            selectinload(Post.tags),
            defer(Post.content, raiseload=True),  # accidental access fails loudly
        )
        .where(*conditions)
        .order_by(*order_by)
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    return [(post, preview) for post, preview in rows], total or 0


async def list_public(session: AsyncSession, filters: PostFilters) -> tuple[list[PostRow], int]:
    conditions = list(IS_PUBLIC)
    if filters.tag:
        conditions.append(Post.tags.any(Tag.name == filters.tag))
    if filters.author:
        conditions.append(User.username == filters.author)
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
    return await _page(session, conditions, order_by, filters.limit, filters.offset)


async def list_by_author(
    session: AsyncSession, author_id: uuid.UUID, filters: MyPostFilters
) -> tuple[list[PostRow], int]:
    conditions = [Post.author_id == author_id, Post.deleted_at.is_(None)]
    if filters.status:
        conditions.append(Post.status == filters.status)
    order_by = (Post.updated_at.desc(), Post.id.desc())
    return await _page(session, conditions, order_by, filters.limit, filters.offset)


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


async def slug_taken(session: AsyncSession, slug: str) -> bool:
    # Deleted posts keep their slug, so an old link can never point at a different post.
    return bool(await session.scalar(select(exists().where(Post.slug == slug))))


async def count_public_by_author(session: AsyncSession, author_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(Post).where(Post.author_id == author_id, *IS_PUBLIC)
    return await session.scalar(stmt) or 0
