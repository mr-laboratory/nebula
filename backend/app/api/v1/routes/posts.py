"""Post endpoints: public feed and reading by slug; create, edit, publish, delete and like by id."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.api.deps import CurrentUser, OptionalUser, RedisDep, SessionDep, SettingsDep
from app.core.rate_limit import enforce
from app.models import PostStatus
from app.schemas.common import Page
from app.schemas.like import LikeStatus
from app.schemas.post import PostCreate, PostDetail, PostFilters, PostSummary, PostUpdate
from app.services import likes, posts

router = APIRouter(prefix="/posts", tags=["posts"])

Slug = Annotated[str, Path(max_length=220)]


@router.get("", summary="Public feed of published posts")
async def list_posts(
    filters: Annotated[PostFilters, Query()], session: SessionDep, viewer: OptionalUser
) -> Page[PostSummary]:
    """`liked_by_me` is filled in when a Bearer token is sent, and null otherwise."""
    return await posts.list_feed(session, filters, viewer)


@router.get("/{slug}", summary="Read a post")
async def read_post(slug: Slug, session: SessionDep, viewer: OptionalUser) -> PostDetail:
    """Published posts are public. A draft is visible only to its author (404 for others)."""
    return await posts.get_visible(session, slug, viewer)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a draft")
async def create_post(
    body: PostCreate,
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    response: Response,
) -> PostDetail:
    post = await posts.create(session, user, body)
    response.headers["Location"] = f"{settings.api_prefix}/posts/{post.slug}"
    return post


@router.patch("/{post_id}", summary="Edit my post")
async def update_post(
    post_id: uuid.UUID, body: PostUpdate, user: CurrentUser, session: SessionDep
) -> PostDetail:
    return await posts.update(session, user, post_id, body)


@router.post("/{post_id}/publish", summary="Publish my post")
async def publish_post(post_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> PostDetail:
    return await posts.set_status(session, user, post_id, PostStatus.PUBLISHED)


@router.post("/{post_id}/unpublish", summary="Move my post back to drafts")
async def unpublish_post(post_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> PostDetail:
    return await posts.set_status(session, user, post_id, PostStatus.DRAFT)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post (owner or moderator)",
)
async def delete_post(post_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    await posts.delete(session, user, post_id)


# Likes are a per-user resource under the post: PUT creates it, DELETE removes it, both idempotent.
LIKE_LIMIT = {"limit": 60, "window": 60}


@router.put("/{post_id}/like", summary="Like a post")
async def like_post(
    post_id: uuid.UUID, user: CurrentUser, session: SessionDep, redis: RedisDep
) -> LikeStatus:
    await enforce(redis, "like:user", str(user.id), **LIKE_LIMIT)
    return await likes.like(session, user, post_id)


@router.delete("/{post_id}/like", summary="Remove my like")
async def unlike_post(
    post_id: uuid.UUID, user: CurrentUser, session: SessionDep, redis: RedisDep
) -> LikeStatus:
    await enforce(redis, "like:user", str(user.id), **LIKE_LIMIT)
    return await likes.unlike(session, user, post_id)
