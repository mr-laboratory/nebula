"""Account management: list accounts, grant and revoke roles, deactivate and reactivate.

Every change is audited. Two rules prevent locking everyone out: an admin can't demote or
deactivate themselves, and the last active admin can't be removed (not even from the CLI).
Changes are serialised with a row lock, so two admins demoting each other at the same moment
can't both succeed. `actor` is None for command-line use, which is trusted (it needs DB access).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models import AuditAction, Role, User
from app.repositories import audit_logs as audit_repo
from app.repositories import users as repo
from app.schemas.admin import AdminUser, AdminUserFilters, AuditLogFilters, AuditLogOut
from app.schemas.common import Page
from app.services import audit
from app.services.auth import DEFAULT_ROLE, revoke_all_sessions
from app.services.permissions import USER_MANAGE, has_permission

ADMIN_ROLE = "admin"
USER_NOT_FOUND = "User not found."
ROLE_NOT_FOUND = "Role not found."
LAST_ADMIN = "This is the last active admin. Make someone else an admin first."


def _out(user: User) -> AdminUser:
    return AdminUser(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=sorted(role.name for role in user.roles),
        created_at=user.created_at,
    )


# ─── Reading ──────────────────────────────────────────────


async def list_users(session: AsyncSession, filters: AdminUserFilters) -> Page[AdminUser]:
    users, total = await repo.list_filtered(session, filters)
    return Page(
        items=[_out(u) for u in users], total=total, limit=filters.limit, offset=filters.offset
    )


async def list_audit_logs(session: AsyncSession, filters: AuditLogFilters) -> Page[AuditLogOut]:
    rows, total = await audit_repo.list_filtered(session, filters)
    items = [
        AuditLogOut(
            id=entry.id,
            actor=actor,
            action=AuditAction(entry.action),
            target_type=entry.target_type,
            target_id=entry.target_id,
            details=entry.details,
            created_at=entry.created_at,
        )
        for entry, actor in rows
    ]
    return Page(items=items, total=total, limit=filters.limit, offset=filters.offset)


# ─── Changing ─────────────────────────────────────────────


async def _begin_change(session: AsyncSession, actor: User | None, username: str) -> User:
    """Take the account-management lock, re-check the actor, and load the target with roles.

    The route already checked the permission, but another admin may have removed it while
    this request waited for the lock; checking again after locking closes that gap.
    """
    await session.execute(select(Role.id).where(Role.name == ADMIN_ROLE).with_for_update())
    if actor is not None:
        await session.refresh(actor, ["is_active"])
        if not actor.is_active or not await has_permission(session, actor.id, USER_MANAGE):
            raise ForbiddenError()
    target = await repo.get_with_roles(session, username)
    if target is None:
        raise NotFoundError(USER_NOT_FOUND)
    return target


async def _role(session: AsyncSession, name: str) -> Role:
    role = await session.scalar(select(Role).where(Role.name == name))
    if role is None:
        raise NotFoundError(ROLE_NOT_FOUND)
    return role


def _is_self(actor: User | None, target: User) -> bool:
    return actor is not None and actor.id == target.id


async def _ensure_not_last_admin(session: AsyncSession, target: User) -> None:
    is_admin = any(role.name == ADMIN_ROLE for role in target.roles)
    if (
        is_admin
        and target.is_active
        and await repo.count_active_with_role(session, ADMIN_ROLE) <= 1
    ):
        raise ConflictError(LAST_ADMIN)


async def grant_role(
    session: AsyncSession, actor: User | None, username: str, role_name: str
) -> AdminUser:
    """Idempotent: granting a role the user already has changes (and logs) nothing."""
    target = await _begin_change(session, actor, username)
    role = await _role(session, role_name)
    if role not in target.roles:
        target.roles.append(role)
        audit.record(session, actor, AuditAction.ROLE_GRANT, "user", target.id, role=role.name)
        await session.flush()
    return _out(target)


async def revoke_role(
    session: AsyncSession, actor: User | None, username: str, role_name: str
) -> AdminUser:
    if role_name == DEFAULT_ROLE:
        raise ConflictError(f"Every account keeps the '{DEFAULT_ROLE}' role.")
    target = await _begin_change(session, actor, username)
    role = await _role(session, role_name)
    if role in target.roles:
        if role.name == ADMIN_ROLE:
            if _is_self(actor, target):
                raise ConflictError("You can't remove your own admin role.")
            await _ensure_not_last_admin(session, target)
        target.roles.remove(role)
        audit.record(session, actor, AuditAction.ROLE_REVOKE, "user", target.id, role=role.name)
        await session.flush()
    return _out(target)


async def set_active(
    session: AsyncSession, actor: User | None, username: str, *, active: bool
) -> AdminUser:
    """Deactivate (blocked from signing in, signed out everywhere, profile hidden) or undo it.

    Deactivation, not deletion: content and audit history stay, and it can be reversed.
    Access tokens stop working at once too, because every request re-checks `is_active`.
    """
    target = await _begin_change(session, actor, username)
    if target.is_active == active:
        return _out(target)
    if not active:
        if _is_self(actor, target):
            raise ConflictError("You can't deactivate your own account.")
        await _ensure_not_last_admin(session, target)
        await revoke_all_sessions(session, target.id)
    target.is_active = active
    action = AuditAction.USER_ACTIVATE if active else AuditAction.USER_DEACTIVATE
    audit.record(session, actor, action, "user", target.id)
    await session.flush()
    return _out(target)
