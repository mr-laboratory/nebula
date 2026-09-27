"""Audit log queries: filtered listing, newest first, with each actor's username."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User
from app.schemas.admin import AuditLogFilters


async def list_filtered(
    session: AsyncSession, filters: AuditLogFilters
) -> tuple[list[tuple[AuditLog, str | None]], int]:
    conditions = []
    if filters.action:
        conditions.append(AuditLog.action == filters.action)
    if filters.actor:
        conditions.append(
            AuditLog.actor_id.in_(select(User.id).where(User.username == filters.actor))
        )
    if filters.target_id:
        conditions.append(AuditLog.target_id == filters.target_id)

    total = await session.scalar(select(func.count()).select_from(AuditLog).where(*conditions))
    stmt = (
        select(AuditLog, User.username)
        .outerjoin(User, User.id == AuditLog.actor_id)  # NULL actor: command line
        .where(*conditions)
        .order_by(AuditLog.id.desc())
        .limit(filters.limit)
        .offset(filters.offset)
    )
    rows: list[tuple[AuditLog, str | None]] = [
        (entry, username) for entry, username in (await session.execute(stmt)).all()
    ]
    return rows, total or 0
