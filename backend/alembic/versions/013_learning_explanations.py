"""learning explanations and citations

Revision ID: 013_learning_explanations
Revises: 012_export_report_pdf_docx
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "013_learning_explanations"
down_revision = "012_export_report_pdf_docx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_explanations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.String(128), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("output_language", sa.String(2), nullable=False),
        sa.Column("section_id", UUID(as_uuid=False), sa.ForeignKey("paper_sections.id", ondelete="CASCADE"), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("evidence_id", UUID(as_uuid=False), sa.ForeignKey("evidences.id", ondelete="CASCADE"), nullable=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("key_points", JSONB(), nullable=True),
        sa.Column("terms", JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("mode IN ('SUMMARY', 'EXPLAIN', 'TRANSLATE')", name="ck_learning_mode_values"),
        sa.CheckConstraint("scope_type IN ('SECTION', 'PAGE', 'EVIDENCE')", name="ck_learning_scope_type_values"),
        sa.CheckConstraint("output_language IN ('zh', 'en')", name="ck_learning_output_language_values"),
        sa.CheckConstraint("status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')", name="ck_learning_status_values"),
        sa.CheckConstraint(
            "(scope_type = 'SECTION' AND section_id IS NOT NULL AND page_number IS NULL AND evidence_id IS NULL) OR "
            "(scope_type = 'PAGE' AND section_id IS NULL AND page_number IS NOT NULL AND page_number >= 1 AND evidence_id IS NULL) OR "
            "(scope_type = 'EVIDENCE' AND section_id IS NULL AND page_number IS NULL AND evidence_id IS NOT NULL)",
            name="ck_learning_scope_exclusive",
        ),
        sa.CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_learning_request_hash_hex64",
        ),
        sa.CheckConstraint(
            "status = 'PENDING' AND answer IS NULL AND key_points IS NULL AND terms IS NULL AND error_message IS NULL AND started_at IS NULL AND completed_at IS NULL OR "
            "status != 'PENDING'",
            name="ck_learning_pending_no_result",
        ),
        sa.CheckConstraint(
            "(status = 'RUNNING') = (started_at IS NOT NULL AND answer IS NULL AND key_points IS NULL AND terms IS NULL AND error_message IS NULL AND completed_at IS NULL)",
            name="ck_learning_running_state",
        ),
        sa.CheckConstraint(
            "(status = 'SUCCEEDED') = (started_at IS NOT NULL AND completed_at IS NOT NULL AND length(btrim(answer)) > 0 AND jsonb_typeof(key_points) = 'array' AND jsonb_array_length(key_points) > 0 AND jsonb_typeof(terms) = 'array' AND jsonb_array_length(terms) > 0 AND error_message IS NULL)",
            name="ck_learning_succeeded_state",
        ),
        sa.CheckConstraint(
            "(status = 'FAILED') = (started_at IS NOT NULL AND completed_at IS NOT NULL AND error_message = '学习解释生成失败，请稍后重试' AND answer IS NULL AND key_points IS NULL AND terms IS NULL)",
            name="ck_learning_failed_state",
        ),
    )
    op.create_index("idx_learning_user_paper", "learning_explanations", ["user_id", "paper_id"])
    op.create_index("idx_learning_paper_created", "learning_explanations", ["paper_id", sa.text("created_at DESC"), sa.text("id DESC")])
    op.create_index("idx_learning_status", "learning_explanations", ["status"])
    op.execute(
        "CREATE UNIQUE INDEX uq_active_learning_request ON learning_explanations "
        "(user_id, paper_id, request_hash) "
        "WHERE status IN ('PENDING', 'RUNNING', 'SUCCEEDED')"
    )

    op.create_table(
        "learning_citations",
        sa.Column("explanation_id", UUID(as_uuid=False), sa.ForeignKey("learning_explanations.id", ondelete="CASCADE"), nullable=False, primary_key=True),
        sa.Column("evidence_id", UUID(as_uuid=False), sa.ForeignKey("evidences.id", ondelete="RESTRICT"), nullable=False, primary_key=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.CheckConstraint("sequence >= 1", name="ck_learning_citation_sequence_positive"),
        sa.UniqueConstraint("explanation_id", "sequence", name="uq_learning_citation_sequence"),
    )
    op.create_index("idx_learning_citation_evidence", "learning_citations", ["evidence_id"])


def downgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT COUNT(*) FROM learning_explanations")).scalar()
    if result and int(result) > 0:
        raise RuntimeError("Cannot downgrade 013: learning_explanations table is not empty")
    result2 = conn.execute(sa.text("SELECT COUNT(*) FROM learning_citations")).scalar()
    if result2 and int(result2) > 0:
        raise RuntimeError("Cannot downgrade 013: learning_citations table is not empty")
    op.drop_table("learning_citations")
    op.drop_table("learning_explanations")
