"""Admin schemas: account listing and filters, and audit log entries. Admin-only responses."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from app.models import AuditAction
from app.schemas.common import PageParams, lowercase

RoleName = Annotated[str, BeforeValidator(lowercase), Field(pattern=r"^[a-z_]{1,30}$")]
Username = Annotated[str, BeforeValidator(lowercase), Field(max_length=30)]


class AdminUserFilters(PageParams):
    q: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | (
        None
    ) = Field(default=None, description="Matches username, display name or email")
    role: RoleName | None = None
    is_active: bool | None = None


class AdminUser(BaseModel):
    """An account as an admin sees it: includes email and status, never the password hash."""

    id: uuid.UUID
    username: str
    email: str
    display_name: str
    is_active: bool
    roles: list[str]
    created_at: datetime


class AuditLogFilters(PageParams):
    action: AuditAction | None = None
    actor: Username | None = Field(default=None, description="Username of who acted")
    target_id: uuid.UUID | None = None


class AuditLogOut(BaseModel):
    id: int
    actor: str | None = Field(description="Username, or null for command-line actions")
    action: AuditAction
    target_type: str
    target_id: uuid.UUID
    details: dict[str, Any]
    created_at: datetime
