"""harden learning explanation contracts without changing business rows

Revision ID: 014_learning_contract_hardening
Revises: 013_learning_explanations
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "014_learning_contract_hardening"
down_revision = "013_learning_explanations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("uq_active_learning_request", table_name="learning_explanations")
    op.drop_constraint(
        "ck_learning_request_hash_hex64", "learning_explanations", type_="check"
    )
    op.drop_constraint(
        "ck_learning_succeeded_state", "learning_explanations", type_="check"
    )
    op.drop_constraint(
        "ck_learning_failed_state", "learning_explanations", type_="check"
    )
    op.alter_column(
        "learning_explanations", "request_hash", existing_type=sa.String(length=64), nullable=False
    )
    op.create_check_constraint(
        "ck_learning_request_hash_hex64",
        "learning_explanations",
        "request_hash ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_learning_succeeded_state",
        "learning_explanations",
        "(status = 'SUCCEEDED') = (started_at IS NOT NULL AND completed_at IS NOT NULL "
        "AND length(btrim(answer)) > 0 AND jsonb_typeof(key_points) = 'array' "
        "AND jsonb_array_length(key_points) > 0 AND jsonb_typeof(terms) = 'array' "
        "AND jsonb_array_length(terms) > 0 AND error_message IS NULL)",
    )
    op.create_check_constraint(
        "ck_learning_failed_state",
        "learning_explanations",
        "(status = 'FAILED') = (started_at IS NOT NULL AND completed_at IS NOT NULL "
        "AND error_message = '学习解释生成失败，请稍后重试' AND answer IS NULL "
        "AND key_points IS NULL AND terms IS NULL)",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_active_learning_request ON learning_explanations "
        "(user_id, paper_id, request_hash) "
        "WHERE status IN ('PENDING', 'RUNNING', 'SUCCEEDED')"
    )


def downgrade() -> None:
    op.drop_index("uq_active_learning_request", table_name="learning_explanations")
    op.drop_constraint(
        "ck_learning_failed_state", "learning_explanations", type_="check"
    )
    op.drop_constraint(
        "ck_learning_succeeded_state", "learning_explanations", type_="check"
    )
    op.drop_constraint(
        "ck_learning_request_hash_hex64", "learning_explanations", type_="check"
    )
    op.alter_column(
        "learning_explanations", "request_hash", existing_type=sa.String(length=64), nullable=True
    )
    op.create_check_constraint(
        "ck_learning_request_hash_hex64",
        "learning_explanations",
        "request_hash IS NULL OR request_hash ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_learning_succeeded_state",
        "learning_explanations",
        "(status = 'SUCCEEDED') = (started_at IS NOT NULL AND completed_at IS NOT NULL "
        "AND answer IS NOT NULL AND key_points IS NOT NULL AND terms IS NOT NULL "
        "AND error_message IS NULL)",
    )
    op.create_check_constraint(
        "ck_learning_failed_state",
        "learning_explanations",
        "(status = 'FAILED') = (started_at IS NOT NULL AND completed_at IS NOT NULL "
        "AND error_message IS NOT NULL AND answer IS NULL AND key_points IS NULL "
        "AND terms IS NULL)",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_active_learning_request ON learning_explanations "
        "(user_id, paper_id, request_hash) WHERE request_hash IS NOT NULL "
        "AND status IN ('PENDING', 'RUNNING', 'SUCCEEDED')"
    )
