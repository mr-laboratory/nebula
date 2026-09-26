"""Comment rules: who can read, write, edit and delete comments.

Anyone who can read a post can read its comments. Signed-in users comment on published posts.
Only the comment's author may edit it; its author, the post's author or a moderator may delete it.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError
from app.models import Comment, Post, User
from app.repositories import comments as repo
from app.schemas.comment import CommentCreate, CommentOut, CommentUpdate
from app.schemas.common import Page, PageParams
from app.schemas.user import AuthorPublic
from app.services.permissions import COMMENT_DELETE_ANY, has_permission
from app.services.posts import get_published, get_readable

COMMENT_NOT_FOUND = "Comment not found."


def _out(comment: Comment) -> CommentOut:
    deleted = comment.is_deleted
    return CommentOut(
        id=comment.id,
        body=None if deleted else comment.body,
        author=None if deleted else AuthorPublic.model_validate(comment.author),
        is_deleted=deleted,
        edited=not deleted and comment.updated_at > comment.created_at,
        created_at=comment.created_at,
    )


async def list_for_post(
    session: AsyncSession, post_id: uuid.UUID, viewer: User | None, params: PageParams
) -> Page[CommentOut]:
    post = await get_readable(session, post_id, viewer)
    comments, total = await repo.list_for_post(session, post.id, params.limit, params.offset)
    return Page(
        items=[_out(c) for c in comments], total=total, limit=params.limit, offset=params.offset
    )


async def _reload(session: AsyncSession, comment_id: uuid.UUID) -> CommentOut:
    comment = await repo.get(session, comment_id)
    assert comment is not None  # noqa: S101  (we just wrote it in this transaction)
    return _out(comment)


async def create(
    session: AsyncSession, user: User, post_id: uuid.UUID, data: CommentCreate
) -> CommentOut:
    post = await get_published(session, post_id, user)
    comment = Comment(id=uuid.uuid4(), post_id=post.id, author_id=user.id, body=data.body)
    session.add(comment)
    await session.flush()
    return await _reload(session, comment.id)


async def _get_for_change(
    session: AsyncSession, comment_id: uuid.UUID, user: User
) -> tuple[Comment, Post]:
    """The comment and its post, if it exists and `user` can still read the post; else 404."""
    comment = await repo.get(session, comment_id)
    if comment is None:
        raise NotFoundError(COMMENT_NOT_FOUND)
    try:
        post = await get_readable(session, comment.post_id, user)
    except NotFoundError:
        raise NotFoundError(COMMENT_NOT_FOUND) from None
    return comment, post


async def update(
    session: AsyncSession, user: User, comment_id: uuid.UUID, data: CommentUpdate
) -> CommentOut:
    comment, _ = await _get_for_change(session, comment_id, user)
    if comment.author_id != user.id:
        raise ForbiddenError("You can only edit your own comments.")
    if comment.body != data.body:  # an unchanged body doesn't mark it as edited
        comment.body = data.body
        await session.flush()
    return await _reload(session, comment.id)


async def delete(session: AsyncSession, user: User, comment_id: uuid.UUID) -> None:
    comment, post = await _get_for_change(session, comment_id, user)
    allowed = (
        user.id in (comment.author_id, post.author_id)  # own comment, or a comment on own post
        or await has_permission(session, user.id, COMMENT_DELETE_ANY)
    )
    if not allowed:
        raise ForbiddenError("You can only delete your own comments.")
    comment.deleted_at = datetime.now(UTC)
    await session.flush()
