"""add admin audit logs

Revision ID: 017_admin_audit_logs
Revises: 016_personal_learning_library
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "017_admin_audit_logs"
down_revision = "016_personal_learning_library"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("actor_user_id", sa.String(128), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("resource_type", sa.String(20), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("before_state", JSONB, nullable=False),
        sa.Column("after_state", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "action IN ('ADMIN_BOOTSTRAPPED', 'USER_ROLE_CHANGED', 'USER_STATUS_CHANGED')",
            name="ck_audit_action_whitelist",
        ),
        sa.CheckConstraint(
            "resource_type = 'USER'",
            name="ck_audit_resource_type_user",
        ),
        sa.CheckConstraint(
            "reason = btrim(reason) AND char_length(reason) BETWEEN 8 AND 500",
            name="ck_audit_reason_length",
        ),
        sa.CheckConstraint(
            "reason !~ '[[:cntrl:]]'",
            name="ck_audit_reason_no_control_chars",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(before_state) = 'object'",
            name="ck_audit_before_state_is_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(after_state) = 'object'",
            name="ck_audit_after_state_is_object",
        ),
        sa.CheckConstraint(
            "CASE "
            "WHEN action = 'ADMIN_BOOTSTRAPPED' THEN "
            "before_state = '{\"role\": \"USER\", \"status\": \"ACTIVE\"}'::jsonb AND "
            "after_state = '{\"role\": \"ADMIN\", \"status\": \"ACTIVE\"}'::jsonb "
            "WHEN action = 'USER_ROLE_CHANGED' THEN "
            "before_state ? 'role' AND before_state - 'role' = '{}'::jsonb AND "
            "after_state ? 'role' AND after_state - 'role' = '{}'::jsonb AND "
            "before_state->>'role' IN ('USER', 'ADMIN') AND "
            "after_state->>'role' IN ('USER', 'ADMIN') AND before_state <> after_state "
            "WHEN action = 'USER_STATUS_CHANGED' THEN "
            "before_state ? 'status' AND before_state - 'status' = '{}'::jsonb AND "
            "after_state ? 'status' AND after_state - 'status' = '{}'::jsonb AND "
            "before_state->>'status' IN ('ACTIVE', 'DISABLED') AND "
            "after_state->>'status' IN ('ACTIVE', 'DISABLED') AND before_state <> after_state "
            "ELSE FALSE END",
            name="ck_audit_state_matches_action",
        ),
    )
    op.create_index("idx_audit_actor", "admin_audit_logs", ["actor_user_id"])
    op.create_index("idx_audit_resource", "admin_audit_logs", ["resource_type", "resource_id"])
    op.create_index("idx_audit_action", "admin_audit_logs", ["action"])
    op.create_index("idx_audit_created", "admin_audit_logs", [sa.text("created_at DESC"), sa.text("id DESC")])

    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'admin_audit_logs is append-only: % operation not permitted', TG_OP;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_prevent_audit_update
            BEFORE UPDATE ON admin_audit_logs
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

        CREATE TRIGGER trg_prevent_audit_delete
            BEFORE DELETE ON admin_audit_logs
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
    """)


def downgrade() -> None:
    bind = op.get_bind()
    total = bind.execute(sa.text('SELECT count(*) FROM "admin_audit_logs"')).scalar_one()
    if total:
        raise RuntimeError("admin_audit_logs contains data; refusing destructive downgrade")

    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_delete ON admin_audit_logs")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_update ON admin_audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_modification()")
    op.drop_table("admin_audit_logs")
