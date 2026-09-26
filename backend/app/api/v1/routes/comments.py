"""Comment endpoints: list and add comments on a post; edit and delete a comment by id."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, OptionalUser, RedisDep, SessionDep
from app.core.rate_limit import enforce
from app.schemas.comment import CommentCreate, CommentOut, CommentUpdate
from app.schemas.common import Page, PageParams
from app.services import comments

router = APIRouter(tags=["comments"])


@router.get("/posts/{post_id}/comments", summary="Comments on a post, oldest first")
async def list_comments(
    post_id: uuid.UUID,
    params: Annotated[PageParams, Query()],
    session: SessionDep,
    viewer: OptionalUser,
) -> Page[CommentOut]:
    return await comments.list_for_post(session, post_id, viewer, params)


@router.post(
    "/posts/{post_id}/comments", status_code=status.HTTP_201_CREATED, summary="Add a comment"
)
async def create_comment(
    post_id: uuid.UUID,
    body: CommentCreate,
    user: CurrentUser,
    session: SessionDep,
    redis: RedisDep,
) -> CommentOut:
    await enforce(redis, "comment:user", str(user.id), limit=10, window=60)
    return await comments.create(session, user, post_id, body)


@router.patch("/comments/{comment_id}", summary="Edit my comment")
async def update_comment(
    comment_id: uuid.UUID,
    body: CommentUpdate,
    user: CurrentUser,
    session: SessionDep,
    redis: RedisDep,
) -> CommentOut:
    await enforce(redis, "comment-edit:user", str(user.id), limit=30, window=60)
    return await comments.update(session, user, comment_id, body)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment (its author, the post's author or a moderator)",
)
async def delete_comment(comment_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    await comments.delete(session, user, comment_id)
