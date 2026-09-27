"""User queries for account management: filtered listing and lookups with roles loaded."""

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Role, User
from app.repositories.posts import escape_like
from app.schemas.admin import AdminUserFilters


def _with_roles(stmt: Select[User]) -> Select[User]:
    return stmt.options(selectinload(User.roles)).execution_options(populate_existing=True)


async def get_with_roles(session: AsyncSession, username: str) -> User | None:
    return await session.scalar(_with_roles(select(User).where(User.username == username)))


async def list_filtered(session: AsyncSession, filters: AdminUserFilters) -> tuple[list[User], int]:
    """Accounts matching the filters, newest first, with the total count."""
    conditions = []
    if filters.q:
        pattern = f"%{escape_like(filters.q)}%"
        conditions.append(
            or_(
                User.username.ilike(pattern, escape="\\"),
                User.display_name.ilike(pattern, escape="\\"),
                User.email.ilike(pattern, escape="\\"),
            )
        )
    if filters.role:
        conditions.append(User.roles.any(Role.name == filters.role))
    if filters.is_active is not None:
        conditions.append(User.is_active.is_(filters.is_active))

    total = await session.scalar(select(func.count()).select_from(User).where(*conditions))
    stmt = (
        select(User)
        .where(*conditions)
        .order_by(User.created_at.desc(), User.id)
        .limit(filters.limit)
        .offset(filters.offset)
    )
    users = (await session.scalars(_with_roles(stmt))).all()
    return list(users), total or 0


async def count_active_with_role(session: AsyncSession, role: str) -> int:
    stmt = select(func.count()).where(User.is_active, User.roles.any(Role.name == role))
    return await session.scalar(stmt) or 0
