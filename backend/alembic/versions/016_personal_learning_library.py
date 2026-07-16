"""add personal learning and library tables

Revision ID: 016_personal_learning_library
Revises: 015_paper_qa_conversations
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "016_personal_learning_library"
down_revision = "015_paper_qa_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_library_entries",
        sa.Column("user_id", sa.String(128), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, primary_key=True),
        sa.Column("reading_status", sa.String(20), nullable=False, server_default="TO_READ"),
        sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("collection_name", sa.String(100), nullable=True),
        sa.Column("last_page", sa.Integer(), nullable=True),
        sa.Column("furthest_page", sa.Integer(), nullable=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("reading_status IN ('TO_READ', 'READING', 'COMPLETED', 'ARCHIVED')", name="ck_library_reading_status_values"),
        sa.CheckConstraint("collection_name IS NULL OR (collection_name = btrim(collection_name) AND char_length(collection_name) BETWEEN 1 AND 100)", name="ck_library_collection_name_trimmed"),
        sa.CheckConstraint("last_page IS NULL OR last_page >= 1", name="ck_library_last_page_positive"),
        sa.CheckConstraint("furthest_page IS NULL OR furthest_page >= 1", name="ck_library_furthest_page_positive"),
        sa.CheckConstraint("last_page IS NULL OR furthest_page IS NULL OR last_page <= furthest_page", name="ck_library_last_le_furthest"),
        sa.CheckConstraint("(reading_status = 'COMPLETED') = (completed_at IS NOT NULL)", name="ck_library_completed_has_date"),
    )
    op.create_index("idx_library_user_status_favorite_collection", "paper_library_entries", ["user_id", "reading_status", "favorite", "collection_name"])
    op.create_index("idx_library_user_last_read_paper", "paper_library_entries", ["user_id", sa.text("last_read_at DESC"), sa.text("paper_id DESC")])

    op.create_table(
        "paper_highlights",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.String(128), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("quoted_text", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="YELLOW"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("page_number >= 1", name="ck_highlight_page_positive"),
        sa.CheckConstraint("char_start >= 0", name="ck_highlight_char_start_nonneg"),
        sa.CheckConstraint("char_end > char_start", name="ck_highlight_char_end_gt_start"),
        sa.CheckConstraint("char_length(quoted_text) <= 5000 AND char_length(btrim(quoted_text)) >= 1", name="ck_highlight_quoted_text_valid"),
        sa.CheckConstraint("color IN ('YELLOW', 'GREEN', 'BLUE', 'PINK')", name="ck_highlight_color_values"),
        sa.CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="ck_highlight_source_hash_hex64"),
        sa.UniqueConstraint("user_id", "paper_id", "page_number", "char_start", "char_end", name="uq_highlight_user_paper_range"),
    )
    op.create_index("idx_highlight_user_paper_page_range", "paper_highlights", ["user_id", "paper_id", "page_number", "char_start", "id"])

    op.create_table(
        "paper_bookmarks",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.String(128), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("page_number >= 1", name="ck_bookmark_page_positive"),
        sa.CheckConstraint("label IS NULL OR (label = btrim(label) AND char_length(label) BETWEEN 1 AND 100)", name="ck_bookmark_label_trimmed"),
        sa.UniqueConstraint("user_id", "paper_id", "page_number", name="uq_bookmark_user_paper_page"),
    )
    op.create_index("idx_bookmark_user_paper_page_id", "paper_bookmarks", ["user_id", "paper_id", "page_number", "id"])

    op.create_table(
        "paper_notes",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.String(128), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("anchor_type", sa.String(20), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("highlight_id", UUID(as_uuid=False), sa.ForeignKey("paper_highlights.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("anchor_type IN ('PAPER', 'PAGE', 'HIGHLIGHT')", name="ck_note_anchor_type_values"),
        sa.CheckConstraint("page_number IS NULL OR page_number >= 1", name="ck_note_page_positive"),
        sa.CheckConstraint("content = btrim(content) AND char_length(content) BETWEEN 1 AND 20000", name="ck_note_content_valid"),
        sa.CheckConstraint("(anchor_type = 'PAPER' AND page_number IS NULL AND highlight_id IS NULL) OR (anchor_type = 'PAGE' AND page_number IS NOT NULL AND highlight_id IS NULL) OR (anchor_type = 'HIGHLIGHT' AND page_number IS NULL AND highlight_id IS NOT NULL)", name="ck_note_anchor_exclusive"),
    )
    op.create_index("idx_note_user_paper_created_id", "paper_notes", ["user_id", "paper_id", sa.text("created_at DESC"), sa.text("id DESC")])
    op.create_index("idx_note_user_paper_anchor", "paper_notes", ["user_id", "paper_id", "anchor_type", "page_number", "highlight_id"])

    op.create_table(
        "paper_knowledge_cards",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.String(128), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_note_id", UUID(as_uuid=False), sa.ForeignKey("paper_notes.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_highlight_id", UUID(as_uuid=False), sa.ForeignKey("paper_highlights.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("front", sa.Text(), nullable=False),
        sa.Column("back", sa.Text(), nullable=False),
        sa.Column("mastery_status", sa.String(20), nullable=False, server_default="NEW"),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("mastery_status IN ('NEW', 'LEARNING', 'MASTERED')", name="ck_card_mastery_status_values"),
        sa.CheckConstraint("front = btrim(front) AND char_length(front) BETWEEN 1 AND 2000", name="ck_card_front_valid"),
        sa.CheckConstraint("back = btrim(back) AND char_length(back) BETWEEN 1 AND 10000", name="ck_card_back_valid"),
        sa.CheckConstraint("NOT (source_note_id IS NOT NULL AND source_highlight_id IS NOT NULL)", name="ck_card_source_exclusive"),
    )
    op.create_index("idx_card_user_paper_updated_id", "paper_knowledge_cards", ["user_id", "paper_id", sa.text("updated_at DESC"), sa.text("id DESC")])
    op.create_index("idx_card_user_paper_mastery_archived", "paper_knowledge_cards", ["user_id", "paper_id", "mastery_status", "archived"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = (
        "paper_library_entries",
        "paper_highlights",
        "paper_bookmarks",
        "paper_notes",
        "paper_knowledge_cards",
    )
    total = sum(bind.execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar_one() for table in tables)
    if total:
        raise RuntimeError("P7.3 tables contain data; refusing destructive downgrade")
    op.drop_table("paper_knowledge_cards")
    op.drop_table("paper_notes")
    op.drop_table("paper_bookmarks")
    op.drop_table("paper_highlights")
    op.drop_table("paper_library_entries")
