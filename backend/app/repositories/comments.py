"""Comment queries: a post's comments oldest first with their authors, in two queries per page."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.models import Comment


async def list_for_post(
    session: AsyncSession, post_id: uuid.UUID, limit: int, offset: int
) -> tuple[list[Comment], int]:
    """Deleted comments are included so the client can show a placeholder in their place."""
    total = await session.scalar(
        select(func.count()).select_from(Comment).where(Comment.post_id == post_id)
    )
    stmt = (
        select(Comment)
        .join(Comment.author)
        .options(contains_eager(Comment.author))
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.scalars(stmt)).all()), total or 0


async def get(session: AsyncSession, comment_id: uuid.UUID) -> Comment | None:
    """A non-deleted comment with its author, always with fresh column values."""
    stmt = (
        select(Comment)
        .join(Comment.author)
        .options(contains_eager(Comment.author))
        .where(Comment.id == comment_id, Comment.deleted_at.is_(None))
        .execution_options(populate_existing=True)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
