"""Blog posts. Drafts are private to their author; deletes are soft (deleted_at)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tag import post_tags

if TYPE_CHECKING:
    from app.models.tag import Tag
    from app.models.user import User


class PostStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Post(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint(
            "status <> 'published' OR published_at IS NOT NULL", name="published_has_date"
        ),
    )

    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True)
    excerpt: Mapped[str | None] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    cover_image_key: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[PostStatus] = mapped_column(
        Enum(
            PostStatus,
            name="post_status",
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=PostStatus.DRAFT,
        server_default=PostStatus.DRAFT.value,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship(lazy="raise")
    tags: Mapped[list[Tag]] = relationship(secondary=post_tags, lazy="raise")
