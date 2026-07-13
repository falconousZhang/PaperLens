"""constraints and hardening

Revision ID: 002_constraints
Revises: 001_initial
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = "002_constraints"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint("ck_paper_page_number_gte1", "paper_pages", "page_number >= 1")
    op.create_check_constraint("ck_paper_table_page_number_gte1", "paper_tables", "page_number >= 1")
    op.create_check_constraint("ck_paper_table_table_index_gte1", "paper_tables", "table_index >= 1")
    op.create_check_constraint("ck_analysis_task_progress_range", "analysis_tasks", "progress BETWEEN 0 AND 100")
    op.create_check_constraint("ck_review_rating_range", "review_results", "rating BETWEEN 1 AND 5")
    op.create_check_constraint("ck_finding_confidence_range", "review_findings", "confidence BETWEEN 0 AND 1")
    op.create_check_constraint("ck_evidence_page_number_gte1", "evidences", "page_number >= 1")
    op.create_check_constraint("ck_evidence_char_start_gte0", "evidences", "char_start >= 0")
    op.create_check_constraint("ck_evidence_char_end_gte_char_start", "evidences", "char_end >= char_start")
    op.create_check_constraint("ck_evidence_bbox_x_valid", "evidences", "bbox_x1 >= bbox_x0")
    op.create_check_constraint("ck_evidence_bbox_y_valid", "evidences", "bbox_y1 >= bbox_y0")
    op.create_check_constraint("ck_paper_table_bbox_x_valid", "paper_tables", "bbox_x1 >= bbox_x0")
    op.create_check_constraint("ck_paper_table_bbox_y_valid", "paper_tables", "bbox_y1 >= bbox_y0")

    op.create_check_constraint(
        "ck_paper_status_values",
        "papers",
        "status IN ('UPLOADING', 'PROCESSING', 'PARSED', 'FAILED')",
    )
    op.create_check_constraint(
        "ck_analysis_task_status_values",
        "analysis_tasks",
        "status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')",
    )
    op.create_check_constraint(
        "ck_evidence_type_values",
        "evidences",
        "evidence_type IN ('TEXT', 'TABLE', 'FIGURE_CAPTION', 'EQUATION')",
    )
    op.create_check_constraint(
        "ck_finding_type_values",
        "review_findings",
        "finding_type IN ('STRENGTH', 'WEAKNESS', 'SUGGESTION')",
    )
    op.create_check_constraint(
        "ck_verification_status_values",
        "review_findings",
        "verification_status IN ('VERIFIED', 'UNVERIFIED', 'PENDING')",
    )
    op.create_check_constraint(
        "ck_export_status_values",
        "export_reports",
        "status IN ('PENDING', 'GENERATING', 'READY', 'FAILED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_export_status_values", "export_reports")
    op.drop_constraint("ck_verification_status_values", "review_findings")
    op.drop_constraint("ck_finding_type_values", "review_findings")
    op.drop_constraint("ck_evidence_type_values", "evidences")
    op.drop_constraint("ck_analysis_task_status_values", "analysis_tasks")
    op.drop_constraint("ck_paper_status_values", "papers")
    op.drop_constraint("ck_paper_table_bbox_y_valid", "paper_tables")
    op.drop_constraint("ck_paper_table_bbox_x_valid", "paper_tables")
    op.drop_constraint("ck_evidence_bbox_y_valid", "evidences")
    op.drop_constraint("ck_evidence_bbox_x_valid", "evidences")
    op.drop_constraint("ck_evidence_char_end_gte_char_start", "evidences")
    op.drop_constraint("ck_evidence_char_start_gte0", "evidences")
    op.drop_constraint("ck_evidence_page_number_gte1", "evidences")
    op.drop_constraint("ck_finding_confidence_range", "review_findings")
    op.drop_constraint("ck_review_rating_range", "review_results")
    op.drop_constraint("ck_analysis_task_progress_range", "analysis_tasks")
    op.drop_constraint("ck_paper_table_table_index_gte1", "paper_tables")
    op.drop_constraint("ck_paper_table_page_number_gte1", "paper_tables")
    op.drop_constraint("ck_paper_page_number_gte1", "paper_pages")