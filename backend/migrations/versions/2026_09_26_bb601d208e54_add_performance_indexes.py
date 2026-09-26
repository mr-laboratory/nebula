"""Add indexes for the feed, search, dashboard, comments and like counts (pg_trgm for search).

Chosen from EXPLAIN ANALYZE on a 10k-post dataset; see docs/database.md. Plain CREATE INDEX
locks writes while it builds, which is fine at this size; a large live table would need
CREATE INDEX CONCURRENTLY outside a transaction instead.

Revision ID: bb601d208e54
Revises: 9b66c05ad4c8
Create Date: 2026-09-26 20:03:16.555190+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bb601d208e54"
down_revision: str | Sequence[str] | None = "9b66c05ad4c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Trigram operator classes for the search indexes (a trusted extension; no superuser needed).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index("ix_comments_author_id", "comments", ["author_id"], unique=False)
    op.create_index(
        "ix_comments_post_created", "comments", ["post_id", "created_at", "id"], unique=False
    )
    op.create_index("ix_likes_post_id", "likes", ["post_id"], unique=False)
    op.create_index("ix_post_tags_tag_id", "post_tags", ["tag_id", "post_id"], unique=False)
    op.create_index(
        "ix_posts_author_updated",
        "posts",
        ["author_id", "updated_at", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_posts_excerpt_trgm",
        "posts",
        ["excerpt"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"excerpt": "gin_trgm_ops"},
        postgresql_where=sa.text("status = 'published' AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_posts_feed",
        "posts",
        ["published_at", "id"],
        unique=False,
        postgresql_where=sa.text("status = 'published' AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_posts_title_trgm",
        "posts",
        ["title"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
        postgresql_where=sa.text("status = 'published' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_posts_title_trgm",
        table_name="posts",
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
        postgresql_where=sa.text("status = 'published' AND deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_posts_feed",
        table_name="posts",
        postgresql_where=sa.text("status = 'published' AND deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_posts_excerpt_trgm",
        table_name="posts",
        postgresql_using="gin",
        postgresql_ops={"excerpt": "gin_trgm_ops"},
        postgresql_where=sa.text("status = 'published' AND deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_posts_author_updated",
        table_name="posts",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index("ix_post_tags_tag_id", table_name="post_tags")
    op.drop_index("ix_likes_post_id", table_name="likes")
    op.drop_index("ix_comments_post_created", table_name="comments")
    op.drop_index("ix_comments_author_id", table_name="comments")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
