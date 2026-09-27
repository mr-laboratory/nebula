"""Add the admin role (user:manage, audit:read) and the append-only audit_logs table.

A trigger rejects UPDATE and DELETE on audit_logs, so even code with a bug (or a mistaken
manual query) cannot rewrite history. Admin gets no moderation rights: roles stay separate.

Revision ID: 59ff4137ce49
Revises: bb601d208e54
Create Date: 2026-09-27 04:32:52.885576+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "59ff4137ce49"
down_revision: str | Sequence[str] | None = "bb601d208e54"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADMIN = ("user:manage", "audit:read")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column(
            "details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_audit_logs_actor_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index("ix_audit_logs_action_id", "audit_logs", ["action", "id"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor_id"), "audit_logs", ["actor_id"], unique=False)
    op.execute(
        """
        CREATE FUNCTION audit_logs_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER audit_logs_append_only BEFORE UPDATE OR DELETE ON audit_logs "
        "FOR EACH ROW EXECUTE FUNCTION audit_logs_append_only()"
    )

    # Reference data: the admin role and its permissions.
    roles = sa.table("roles", sa.column("name", sa.String))
    permissions = sa.table("permissions", sa.column("code", sa.String))
    op.bulk_insert(roles, [{"name": "admin"}])
    op.bulk_insert(permissions, [{"code": code} for code in ADMIN])
    op.execute(
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r CROSS JOIN permissions p "
            "WHERE r.name = 'admin' AND p.code = ANY(:codes)"
        ).bindparams(codes=list(ADMIN))
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Cascades to user_roles and role_permissions.
    op.execute("DELETE FROM roles WHERE name = 'admin'")
    op.execute(
        sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(codes=list(ADMIN))
    )
    op.drop_index(op.f("ix_audit_logs_actor_id"), table_name="audit_logs")
    op.drop_index("ix_audit_logs_action_id", table_name="audit_logs")
    op.drop_table("audit_logs")  # drops its trigger too
    op.execute("DROP FUNCTION audit_logs_append_only()")
