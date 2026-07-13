"""add normalized_text_content to paper_pages and error_message to papers

Revision ID: 003_normalized_and_error
Revises: 002_constraints
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = "003_normalized_and_error"
down_revision = "002_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("paper_pages", sa.Column("normalized_text_content", sa.Text(), nullable=True))
    op.add_column("papers", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("papers", "error_message")
    op.drop_column("paper_pages", "normalized_text_content")