"""The signed-in user's own profile: read (with roles and permissions) and update."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Role, User
from app.schemas.user import UserMe, UserUpdate


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
