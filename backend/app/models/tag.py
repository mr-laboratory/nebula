"""Tags and the post_tags junction table (many-to-many between posts and tags)."""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, String, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Uuid, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    # The primary key starts with post_id; filtering the feed by tag starts from tag_id.
    Index("ix_post_tags_tag_id", "tag_id", "post_id"),
)


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (CheckConstraint("name ~ '^[a-z0-9-]{1,40}$'", name="name_format"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
