"""store selected text offsets for learning explanations

Revision ID: 022_learning_selection_offsets
Revises: 021_learning_page_selection
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "022_learning_selection_offsets"
down_revision = "021_learning_page_selection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_explanations",
        sa.Column("selection_start", sa.Integer(), nullable=True),
    )
    op.add_column(
        "learning_explanations",
        sa.Column("selection_end", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_learning_selection_offsets_valid",
        "learning_explanations",
        "(selection_start IS NULL AND selection_end IS NULL) OR "
        "(selection_text IS NOT NULL AND selection_start >= 0 "
        "AND selection_end > selection_start)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_learning_selection_offsets_valid",
        "learning_explanations",
        type_="check",
    )
    op.drop_column("learning_explanations", "selection_end")
    op.drop_column("learning_explanations", "selection_start")
