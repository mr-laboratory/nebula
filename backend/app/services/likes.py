"""Like rules: signed-in users like published posts, never their own. Like/unlike are idempotent."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError
from app.models import User
from app.repositories import likes as repo
from app.repositories import posts as post_repo
from app.schemas.like import LikeStatus
from app.services.posts import get_published, get_readable


async def _status(session: AsyncSession, post_id: uuid.UUID, user: User) -> LikeStatus:
    stats = await post_repo.get_stats(session, post_id, user.id)
    return LikeStatus(like_count=stats.like_count, liked_by_me=stats.liked)


async def like(session: AsyncSession, user: User, post_id: uuid.UUID) -> LikeStatus:
    post = await get_published(session, post_id, user)
    if post.author_id == user.id:
        raise ForbiddenError("You can't like your own post.")
    await repo.add(session, user.id, post.id)
    return await _status(session, post.id, user)


async def unlike(session: AsyncSession, user: User, post_id: uuid.UUID) -> LikeStatus:
    # Readable is enough: taking a like back stays possible after a post is unpublished.
    post = await get_readable(session, post_id, user)
    await repo.remove(session, user.id, post.id)
    return await _status(session, post.id, user)
