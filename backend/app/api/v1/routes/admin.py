"""Admin endpoints: account management (user:manage) and the audit log (audit:read)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import SessionDep, require_permission
from app.models import User
from app.schemas.admin import (
    AdminUser,
    AdminUserFilters,
    AuditLogFilters,
    AuditLogOut,
    RoleName,
    Username,
)
from app.schemas.common import Page
from app.services import admin
from app.services.permissions import AUDIT_READ, USER_MANAGE

router = APIRouter(prefix="/admin", tags=["admin"])

UserManager = Annotated[User, Depends(require_permission(USER_MANAGE))]
AuditReader = Annotated[User, Depends(require_permission(AUDIT_READ))]
UsernamePath = Annotated[Username, Path()]
RolePath = Annotated[RoleName, Path()]


@router.get("/users", summary="List accounts (with email, status and roles)")
async def list_users(
    filters: Annotated[AdminUserFilters, Query()], _: UserManager, session: SessionDep
) -> Page[AdminUser]:
    return await admin.list_users(session, filters)


@router.put("/users/{username}/roles/{role}", summary="Grant a role (idempotent)")
async def grant_role(
    username: UsernamePath, role: RolePath, actor: UserManager, session: SessionDep
) -> AdminUser:
    return await admin.grant_role(session, actor, username, role)


@router.delete("/users/{username}/roles/{role}", summary="Revoke a role (idempotent)")
async def revoke_role(
    username: UsernamePath, role: RolePath, actor: UserManager, session: SessionDep
) -> AdminUser:
    return await admin.revoke_role(session, actor, username, role)


@router.post("/users/{username}/deactivate", summary="Deactivate an account and sign it out")
async def deactivate(username: UsernamePath, actor: UserManager, session: SessionDep) -> AdminUser:
    return await admin.set_active(session, actor, username, active=False)


@router.post("/users/{username}/activate", summary="Reactivate an account")
async def activate(username: UsernamePath, actor: UserManager, session: SessionDep) -> AdminUser:
    return await admin.set_active(session, actor, username, active=True)


@router.get("/audit-logs", summary="Audit log, newest first")
async def list_audit_logs(
    filters: Annotated[AuditLogFilters, Query()], _: AuditReader, session: SessionDep
) -> Page[AuditLogOut]:
    return await admin.list_audit_logs(session, filters)
