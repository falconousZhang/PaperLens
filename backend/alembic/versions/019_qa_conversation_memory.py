"""add reusable paper memory to QA conversations

Revision ID: 019_qa_conversation_memory
Revises: 018_qa_current_page
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "019_qa_conversation_memory"
down_revision = "018_qa_current_page"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "paper_qa_conversations",
        sa.Column("paper_memory", sa.Text(), nullable=True),
    )
    op.add_column(
        "paper_qa_conversations",
        sa.Column("paper_memory_source_hash", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        "ck_qa_conv_paper_memory_state",
        "paper_qa_conversations",
        "(paper_memory IS NULL AND paper_memory_source_hash IS NULL) OR "
        "(paper_memory IS NOT NULL AND btrim(paper_memory) <> '' AND "
        "paper_memory_source_hash ~ '^[0-9a-f]{64}$')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_qa_conv_paper_memory_state",
        "paper_qa_conversations",
        type_="check",
    )
    op.drop_column("paper_qa_conversations", "paper_memory_source_hash")
    op.drop_column("paper_qa_conversations", "paper_memory")
