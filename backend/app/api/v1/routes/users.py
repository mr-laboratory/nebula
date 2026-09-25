"""The signed-in user's own profile (/users/me)."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.user import UserMe, UserUpdate
from app.services import users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", summary="My profile, roles and permissions")
async def read_me(user: CurrentUser, session: SessionDep) -> UserMe:
    return await users.get_me(session, user.id)


@router.patch("/me", summary="Update my profile")
async def update_me(body: UserUpdate, user: CurrentUser, session: SessionDep) -> UserMe:
    return await users.update_me(session, user, body)
