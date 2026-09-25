"""Add refresh_tokens.family_id so a reused token can revoke its whole login session.

Expand/backfill/contract: add the column as nullable, fill existing rows, then make it
NOT NULL, so the migration is safe on a table that already has data.

Revision ID: 9b66c05ad4c8
Revises: f2be670edb27
Create Date: 2026-09-25 18:15:30.878029+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b66c05ad4c8"
down_revision: str | Sequence[str] | None = "f2be670edb27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("refresh_tokens", sa.Column("family_id", sa.Uuid(), nullable=True))
    # Existing tokens each become their own family.
    op.execute("UPDATE refresh_tokens SET family_id = id WHERE family_id IS NULL")
    op.alter_column("refresh_tokens", "family_id", nullable=False)
    op.create_index(
        op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_refresh_tokens_family_id"), table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "family_id")
