"""Likes. The composite primary key (user_id, post_id) makes duplicate likes impossible."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Like(Base):
    __tablename__ = "likes"
    # The primary key starts with user_id, so counting a post's likes needs its own index.
    __table_args__ = (Index("ix_likes_post_id", "post_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
