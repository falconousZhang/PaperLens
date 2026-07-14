"""add users, auth_sessions, password_reset_tokens tables

Revision ID: 004_auth_tables
Revises: 003_normalized_and_error
Create Date: 2026-07-13
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004_auth_tables"
down_revision = "003_normalized_and_error"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("email_normalized", sa.String(320), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="USER"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_user_role_values"),
        sa.CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="ck_user_status_values"),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("sid", UUID(as_uuid=False), primary_key=True),
        sa.Column("family_id", UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("user_id", sa.String(128), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(50), nullable=True),
        sa.Column("replaced_by_id", UUID(as_uuid=False), sa.ForeignKey("auth_sessions.sid", ondelete="SET NULL"), nullable=True),
    )

    op.create_index("idx_auth_session_family", "auth_sessions", ["family_id"])
    op.create_index("idx_auth_session_user", "auth_sessions", ["user_id"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.String(128), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        f"""
        INSERT INTO users (id, email, email_normalized, display_name, password_hash, role, status, failed_login_count)
        VALUES ('demo-user', 'demo@paperlens.local', 'demo@paperlens.local', 'Demo User (Legacy)', '', 'USER', 'DISABLED', 0)
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.create_foreign_key("fk_papers_user_id", "papers", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_analysis_tasks_user_id", "analysis_tasks", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_experiment_files_user_id", "experiment_files", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_export_reports_user_id", "export_reports", "users", ["user_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint("fk_export_reports_user_id", "export_reports", type_="foreignkey")
    op.drop_constraint("fk_experiment_files_user_id", "experiment_files", type_="foreignkey")
    op.drop_constraint("fk_analysis_tasks_user_id", "analysis_tasks", type_="foreignkey")
    op.drop_constraint("fk_papers_user_id", "papers", type_="foreignkey")
    op.drop_table("password_reset_tokens")
    op.drop_table("auth_sessions")
    op.drop_table("users")