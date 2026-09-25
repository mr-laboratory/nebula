"""User endpoints: my profile and my posts (/users/me…), and public author profiles."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import CurrentUser, SessionDep
from app.schemas.common import Page
from app.schemas.post import MyPostFilters, PostSummary
from app.schemas.user import UserMe, UserPublic, UserUpdate
from app.services import posts, users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", summary="My profile, roles and permissions")
async def read_me(user: CurrentUser, session: SessionDep) -> UserMe:
    return await users.get_me(session, user.id)


@router.patch("/me", summary="Update my profile")
async def update_me(body: UserUpdate, user: CurrentUser, session: SessionDep) -> UserMe:
    return await users.update_me(session, user, body)


@router.get("/me/posts", summary="My posts, including drafts")
async def list_my_posts(
    filters: Annotated[MyPostFilters, Query()], user: CurrentUser, session: SessionDep
) -> Page[PostSummary]:
    return await posts.list_mine(session, user, filters)


@router.get("/{username}", summary="Public author profile")
async def read_user(
    username: Annotated[str, Path(max_length=30)], session: SessionDep
) -> UserPublic:
    return await users.get_public(session, username.lower())
