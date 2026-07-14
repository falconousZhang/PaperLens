"""correct authentication constraints and ownership delete policy

Revision ID: 005_auth_security_corrections
Revises: 004_auth_tables
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "005_auth_security_corrections"
down_revision = "004_auth_tables"
branch_labels = None
depends_on = None


_RESOURCE_FOREIGN_KEYS = (
    ("fk_papers_user_id", "papers"),
    ("fk_analysis_tasks_user_id", "analysis_tasks"),
    ("fk_experiment_files_user_id", "experiment_files"),
    ("fk_export_reports_user_id", "export_reports"),
)


def upgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=256),
        nullable=True,
    )
    op.execute("UPDATE users SET password_hash = NULL WHERE id = 'demo-user' AND password_hash = ''")

    op.drop_index("ix_auth_sessions_family_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")

    op.create_index(
        "idx_auth_session_token_hash",
        "auth_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "idx_auth_session_expires_at",
        "auth_sessions",
        ["expires_at"],
    )
    op.create_index(
        "idx_password_reset_user",
        "password_reset_tokens",
        ["user_id"],
    )
    op.create_index(
        "idx_password_reset_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "idx_password_reset_expires_at",
        "password_reset_tokens",
        ["expires_at"],
    )

    op.drop_constraint("auth_sessions_user_id_fkey", "auth_sessions", type_="foreignkey")
    op.create_foreign_key(
        "auth_sessions_user_id_fkey",
        "auth_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "password_reset_tokens_user_id_fkey",
        "password_reset_tokens",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "password_reset_tokens_user_id_fkey",
        "password_reset_tokens",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    for constraint_name, table_name in _RESOURCE_FOREIGN_KEYS:
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table_name,
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    for constraint_name, table_name in reversed(_RESOURCE_FOREIGN_KEYS):
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table_name,
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    op.drop_constraint(
        "password_reset_tokens_user_id_fkey",
        "password_reset_tokens",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "password_reset_tokens_user_id_fkey",
        "password_reset_tokens",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("auth_sessions_user_id_fkey", "auth_sessions", type_="foreignkey")
    op.create_foreign_key(
        "auth_sessions_user_id_fkey",
        "auth_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("idx_password_reset_expires_at", table_name="password_reset_tokens")
    op.drop_index("idx_password_reset_token_hash", table_name="password_reset_tokens")
    op.drop_index("idx_password_reset_user", table_name="password_reset_tokens")
    op.drop_index("idx_auth_session_expires_at", table_name="auth_sessions")
    op.drop_index("idx_auth_session_token_hash", table_name="auth_sessions")

    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_family_id", "auth_sessions", ["family_id"])

    op.execute("UPDATE users SET password_hash = '' WHERE id = 'demo-user' AND password_hash IS NULL")
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=256),
        nullable=False,
    )
