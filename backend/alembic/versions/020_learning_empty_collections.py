"""allow mode-specific empty learning collections

Revision ID: 020_learning_empty_collections
Revises: 019_qa_conversation_memory
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "020_learning_empty_collections"
down_revision = "019_qa_conversation_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_learning_succeeded_state",
        "learning_explanations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_learning_succeeded_state",
        "learning_explanations",
        "(status = 'SUCCEEDED') = (started_at IS NOT NULL AND completed_at IS NOT NULL "
        "AND length(btrim(answer)) > 0 AND jsonb_typeof(key_points) = 'array' "
        "AND jsonb_typeof(terms) = 'array' AND error_message IS NULL)",
    )


def downgrade() -> None:
    empty_results = op.get_bind().execute(
        sa.text(
            "SELECT count(*) FROM learning_explanations "
            "WHERE status = 'SUCCEEDED' AND "
            "(jsonb_array_length(key_points) = 0 OR jsonb_array_length(terms) = 0)"
        )
    ).scalar()
    if empty_results:
        raise RuntimeError(
            "Cannot downgrade 020: successful learning explanations contain empty collections"
        )
    op.drop_constraint(
        "ck_learning_succeeded_state",
        "learning_explanations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_learning_succeeded_state",
        "learning_explanations",
        "(status = 'SUCCEEDED') = (started_at IS NOT NULL AND completed_at IS NOT NULL "
        "AND length(btrim(answer)) > 0 AND jsonb_typeof(key_points) = 'array' "
        "AND jsonb_array_length(key_points) > 0 AND jsonb_typeof(terms) = 'array' "
        "AND jsonb_array_length(terms) > 0 AND error_message IS NULL)",
    )
