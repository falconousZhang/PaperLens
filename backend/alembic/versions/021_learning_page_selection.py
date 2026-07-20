"""store selected page text for learning explanations

Revision ID: 021_learning_page_selection
Revises: 020_learning_empty_collections
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "021_learning_page_selection"
down_revision = "020_learning_empty_collections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_explanations",
        sa.Column("selection_text", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_learning_selection_text_valid",
        "learning_explanations",
        "selection_text IS NULL OR (selection_text = btrim(selection_text) "
        "AND length(selection_text) BETWEEN 1 AND 5000)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_learning_selection_text_valid",
        "learning_explanations",
        type_="check",
    )
    op.drop_column("learning_explanations", "selection_text")
