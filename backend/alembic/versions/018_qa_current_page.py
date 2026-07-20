"""add current page to paper QA turns

Revision ID: 018_qa_current_page
Revises: 017_admin_audit_logs
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "018_qa_current_page"
down_revision = "017_admin_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "paper_qa_turns",
        sa.Column("current_page", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_qa_turn_current_page_positive",
        "paper_qa_turns",
        "current_page IS NULL OR current_page >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_qa_turn_current_page_positive",
        "paper_qa_turns",
        type_="check",
    )
    op.drop_column("paper_qa_turns", "current_page")
