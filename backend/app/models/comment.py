"""Comments on posts by signed-in users. Soft-deleted so threads keep their history."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Comment(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint("char_length(body) BETWEEN 1 AND 5000", name="body_length"),
        # A post's thread in order, and the per-post comment count.
        Index("ix_comments_post_created", "post_id", "created_at", "id"),
        # Deleting a user cascades to their comments; without this that is a full scan.
        Index("ix_comments_author_id", "author_id"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)

    author: Mapped[User] = relationship(lazy="raise")
