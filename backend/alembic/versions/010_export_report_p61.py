"""export report p61 fields

Revision ID: 010_export_report_p61
Revises: 009_exp_analysis_task_link
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "010_export_report_p61"
down_revision = "009_exp_analysis_task_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "export_reports",
        sa.Column("language", sa.String(2), nullable=False, server_default="zh"),
    )
    op.add_column(
        "export_reports",
        sa.Column("include_metrics", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "export_reports",
        sa.Column("include_experiment_analysis", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "export_reports",
        sa.Column("source_snapshot", postgresql.JSONB(), nullable=True),
    )

    op.create_check_constraint(
        "ck_export_report_type_markdown",
        "export_reports",
        "report_type IN ('MARKDOWN', 'PDF', 'DOCX')",
    )
    op.create_check_constraint(
        "ck_export_language_values",
        "export_reports",
        "language IN ('zh', 'en')",
    )
    op.create_check_constraint(
        "ck_export_ready_has_storage",
        "export_reports",
        "source_snapshot IS NULL OR ((status = 'READY') = "
        "(storage_key IS NOT NULL AND content_hash IS NOT NULL AND file_size IS NOT NULL))",
    )
    op.create_check_constraint(
        "ck_export_failed_has_error",
        "export_reports",
        "source_snapshot IS NULL OR ((status = 'FAILED') = (error_message IS NOT NULL))",
    )
    op.create_check_constraint(
        "ck_export_file_size_nonneg",
        "export_reports",
        "file_size IS NULL OR file_size >= 0",
    )

def downgrade() -> None:
    bind = op.get_bind()
    has_data = bind.execute(
        sa.text("SELECT count(*) FROM export_reports")
    ).scalar_one()
    if has_data > 0:
        raise RuntimeError(
            "export_reports contains data; downgrade aborted without modifying user data"
        )

    op.execute(sa.text("DROP INDEX IF EXISTS uq_active_export_per_user_paper_type_lang"))
    op.drop_constraint("ck_export_file_size_nonneg", "export_reports", type_="check")
    op.drop_constraint("ck_export_failed_has_error", "export_reports", type_="check")
    op.drop_constraint("ck_export_ready_has_storage", "export_reports", type_="check")
    op.drop_constraint("ck_export_language_values", "export_reports", type_="check")
    op.drop_constraint("ck_export_report_type_markdown", "export_reports", type_="check")
    op.drop_column("export_reports", "source_snapshot")
    op.drop_column("export_reports", "include_experiment_analysis")
    op.drop_column("export_reports", "include_metrics")
    op.drop_column("export_reports", "language")
