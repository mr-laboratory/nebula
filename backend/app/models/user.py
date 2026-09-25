"""User accounts. Email and password hash are private and never exposed publicly."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.role import Role


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint("username ~ '^[a-z0-9_]{3,30}$'", name="username_format"),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(60))
    bio: Mapped[str | None] = mapped_column(String(280))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())

    roles: Mapped[list[Role]] = relationship(secondary="user_roles", lazy="raise")
