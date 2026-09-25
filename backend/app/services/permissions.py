"""Role-based permission checks. Codes match the reference data seeded by migrations."""

import uuid

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Permission, role_permissions, user_roles

POST_DELETE_ANY = "post:delete:any"
COMMENT_DELETE_ANY = "comment:delete:any"


async def has_permission(session: AsyncSession, user_id: uuid.UUID, code: str) -> bool:
    """True if any of the user's roles grants `code`. One EXISTS query."""
    granted = exists().where(
        user_roles.c.user_id == user_id,
        role_permissions.c.role_id == user_roles.c.role_id,
        Permission.id == role_permissions.c.permission_id,
        Permission.code == code,
    )
    return bool(await session.scalar(select(granted)))
