"""Audit log: an append-only record of privileged actions (moderation and account management).

Entries hold ids and small labels only (like a role name), never copied content or personal
data. A database trigger rejects UPDATE and DELETE, so history cannot be rewritten.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditAction(StrEnum):
    POST_DELETE = "post.delete"
    COMMENT_DELETE = "comment.delete"
    ROLE_GRANT = "role.grant"
    ROLE_REVOKE = "role.revoke"
    USER_DEACTIVATE = "user.deactivate"
    USER_ACTIVATE = "user.activate"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_action_id", "action", "id"),)

    # A sequence, not a UUID: ids are strictly increasing, so "newest first" is ORDER BY id.
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # NULL when the action came from the command line rather than a signed-in user.
    # No ON DELETE: an account with audit history can be deactivated, never erased.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[uuid.UUID]
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
