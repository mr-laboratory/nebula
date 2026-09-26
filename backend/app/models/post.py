"""Blog posts. Drafts are private to their author; deletes are soft (deleted_at)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tag import post_tags

if TYPE_CHECKING:
    from app.models.tag import Tag
    from app.models.user import User


class PostStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


# Partial-index predicates. Queries must repeat them literally (not as bound parameters)
# for the planner to prove an index applies; see IS_PUBLIC in repositories/posts.py.
PUBLIC_PREDICATE = text("status = 'published' AND deleted_at IS NULL")
NOT_DELETED_PREDICATE = text("deleted_at IS NULL")


class Post(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint(
            "status <> 'published' OR published_at IS NOT NULL", name="published_has_date"
        ),
        # Public feed in either sort order (a B-tree reads backwards just as well).
        Index("ix_posts_feed", "published_at", "id", postgresql_where=PUBLIC_PREDICATE),
        # An author's dashboard, newest edit first; also serves the author_id foreign key.
        Index(
            "ix_posts_author_updated",
            "author_id",
            "updated_at",
            "id",
            postgresql_where=NOT_DELETED_PREDICATE,
        ),
        # Trigram indexes let ILIKE '%term%' search use an index instead of reading every row.
        Index(
            "ix_posts_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
            postgresql_where=PUBLIC_PREDICATE,
        ),
        Index(
            "ix_posts_excerpt_trgm",
            "excerpt",
            postgresql_using="gin",
            postgresql_ops={"excerpt": "gin_trgm_ops"},
            postgresql_where=PUBLIC_PREDICATE,
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
