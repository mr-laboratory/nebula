"""User profiles: the signed-in user's own (private) profile and public author profiles."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.models import Role, User
from app.repositories import posts as post_repo
from app.schemas.user import UserMe, UserPublic, UserUpdate


async def get_me(session: AsyncSession, user_id: uuid.UUID) -> UserMe:
    user = (
        await session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    return UserMe(
        id=user.id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        created_at=user.created_at,
        roles=sorted(role.name for role in user.roles),
        permissions=sorted({perm.code for role in user.roles for perm in role.permissions}),
    )


async def update_me(session: AsyncSession, user: User, data: UserUpdate) -> UserMe:
    for field in data.model_fields_set:
        setattr(user, field, getattr(data, field))
    await session.flush()
    return await get_me(session, user.id)


async def get_public(session: AsyncSession, username: str) -> UserPublic:
    """A public profile. Deactivated accounts are hidden, as if they didn't exist."""
    user = await session.scalar(select(User).where(User.username == username, User.is_active))
    if user is None:
        raise NotFoundError("User not found.")
    return UserPublic(
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        created_at=user.created_at,
        post_count=await post_repo.count_public_by_author(session, user.id),
    )
