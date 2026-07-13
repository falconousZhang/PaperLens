"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="UPLOADING"),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_paper_user_id", "papers", ["user_id"])
    op.create_index("idx_paper_file_hash", "papers", ["file_hash"])
    op.create_index("idx_paper_status", "papers", ["status"])

    op.create_table(
        "paper_pages",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("text_content", sa.Text, nullable=True),
        sa.Column("width", sa.Float, nullable=True),
        sa.Column("height", sa.Float, nullable=True),
        sa.UniqueConstraint("paper_id", "page_number", name="uq_paper_page"),
    )

    op.create_table(
        "paper_sections",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("level", sa.Integer, nullable=False, server_default="1"),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("start_page", sa.Integer, nullable=True),
        sa.Column("end_page", sa.Integer, nullable=True),
        sa.Column("text_content", sa.Text, nullable=True),
    )
    op.create_index("idx_paper_section_paper_id", "paper_sections", ["paper_id", "sequence"])

    op.create_table(
        "paper_chunks",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", UUID(as_uuid=False), sa.ForeignKey("paper_sections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("char_count", sa.Integer, nullable=False),
        sa.Column("page_numbers", ARRAY(sa.Integer), nullable=True),
        sa.Column("embedding_id", sa.String(128), nullable=True),
        sa.UniqueConstraint("paper_id", "chunk_index", name="uq_paper_chunk"),
    )

    op.create_table(
        "paper_tables",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("table_index", sa.Integer, nullable=False),
        sa.Column("caption", sa.String(500), nullable=True),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("structured_data", JSONB, nullable=True),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.UniqueConstraint("paper_id", "page_number", "table_index", name="uq_paper_table"),
    )

    op.create_table(
        "evidences",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", UUID(as_uuid=False), sa.ForeignKey("paper_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_id", UUID(as_uuid=False), sa.ForeignKey("paper_sections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quoted_text", sa.Text, nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("char_start", sa.Integer, nullable=True),
        sa.Column("char_end", sa.Integer, nullable=True),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_evidence_paper_id", "evidences", ["paper_id"])
    op.create_index("idx_evidence_chunk_id", "evidences", ["chunk_id"])
    op.create_index("idx_evidence_page", "evidences", ["paper_id", "page_number"])

    op.create_table(
        "analysis_tasks",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("user_id", sa.String(128), nullable=False),
    )
    op.create_index("idx_task_paper_id", "analysis_tasks", ["paper_id"])
    op.create_index("idx_task_status", "analysis_tasks", ["status"])
    op.create_index("idx_task_user_id", "analysis_tasks", ["user_id"])

    op.create_table(
        "review_results",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("task_id", UUID(as_uuid=False), sa.ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dimension", sa.String(50), nullable=False),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("overall_verdict", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_review_task_id", "review_results", ["task_id"])
    op.create_index("idx_review_paper_id", "review_results", ["paper_id"])
    op.create_unique_constraint("uq_review_dimension", "review_results", ["task_id", "dimension"])

    op.create_table(
        "review_findings",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("review_id", UUID(as_uuid=False), sa.ForeignKey("review_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_finding_review_id", "review_findings", ["review_id", "sequence"])
    op.create_index("idx_finding_type", "review_findings", ["review_id", "finding_type"])

    op.create_table(
        "finding_evidences",
        sa.Column("finding_id", UUID(as_uuid=False), sa.ForeignKey("review_findings.id", ondelete="CASCADE"), nullable=False, primary_key=True),
        sa.Column("evidence_id", UUID(as_uuid=False), sa.ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, primary_key=True),
    )

    op.create_table(
        "metric_records",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", UUID(as_uuid=False), sa.ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=True),
        sa.Column("dataset_name", sa.String(200), nullable=True),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.Float, nullable=False),
        sa.Column("checkpoint_type", sa.String(20), nullable=True),
        sa.Column("checkpoint_source", sa.String(50), nullable=True),
        sa.Column("evidence_id", UUID(as_uuid=False), sa.ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("table_id", UUID(as_uuid=False), sa.ForeignKey("paper_tables.id", ondelete="SET NULL"), nullable=True),
        sa.Column("row_index", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_metric_paper_id", "metric_records", ["paper_id"])
    op.create_index("idx_metric_task_id", "metric_records", ["task_id"])
    op.create_index("idx_metric_checkpoint_type", "metric_records", ["checkpoint_type"])

    op.create_table(
        "experiment_files",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("column_count", sa.Integer, nullable=True),
        sa.Column("columns_info", JSONB, nullable=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_exp_file_paper_id", "experiment_files", ["paper_id"])
    op.create_index("idx_exp_file_user_id", "experiment_files", ["user_id"])

    op.create_table(
        "experiment_results",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("file_id", UUID(as_uuid=False), sa.ForeignKey("experiment_files.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("task_id", UUID(as_uuid=False), sa.ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary_stats", JSONB, nullable=False),
        sa.Column("column_analysis", JSONB, nullable=True),
        sa.Column("metric_comparisons", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "export_reports",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("paper_id", UUID(as_uuid=False), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("storage_key", sa.String(1024), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("file_size", sa.BigInteger, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_export_paper_id", "export_reports", ["paper_id"])
    op.create_index("idx_export_user_id", "export_reports", ["user_id"])
    op.create_index("idx_export_status", "export_reports", ["status"])


def downgrade() -> None:
    op.drop_table("export_reports")
    op.drop_table("experiment_results")
    op.drop_table("experiment_files")
    op.drop_table("metric_records")
    op.drop_table("finding_evidences")
    op.drop_table("review_findings")
    op.drop_table("review_results")
    op.drop_table("analysis_tasks")
    op.drop_table("evidences")
    op.drop_table("paper_tables")
    op.drop_table("paper_chunks")
    op.drop_table("paper_sections")
    op.drop_table("paper_pages")
    op.drop_table("papers")
