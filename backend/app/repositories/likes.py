"""Like writes. Both are idempotent: the (user_id, post_id) primary key allows one like each."""

import uuid

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Like


async def add(session: AsyncSession, user_id: uuid.UUID, post_id: uuid.UUID) -> None:
    # ON CONFLICT DO NOTHING: liking twice (even concurrently) is not an error.
    await session.execute(
        insert(Like).values(user_id=user_id, post_id=post_id).on_conflict_do_nothing()
    )


async def remove(session: AsyncSession, user_id: uuid.UUID, post_id: uuid.UUID) -> None:
    await session.execute(delete(Like).where(Like.user_id == user_id, Like.post_id == post_id))
