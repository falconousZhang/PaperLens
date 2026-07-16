"""export report pdf docx

Revision ID: 012_export_report_pdf_docx
Revises: 011_export_report_p61_integrity
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "012_export_report_pdf_docx"
down_revision = "011_export_report_p61_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_export_p61_source", "export_reports", type_="check")
    op.create_check_constraint(
        "ck_export_p61_source",
        "export_reports",
        "source_snapshot IS NULL OR "
        "(report_type IN ('MARKDOWN', 'PDF', 'DOCX') AND "
        "(status = 'FAILED' OR content_hash IS NOT NULL))",
    )


def downgrade() -> None:
    bind = op.get_bind()
    has_pdf_docx = bind.execute(
        sa.text(
            "SELECT count(*) FROM export_reports "
            "WHERE report_type IN ('PDF', 'DOCX')"
        )
    ).scalar_one()
    if has_pdf_docx > 0:
        raise RuntimeError(
            "PDF/DOCX export reports exist; downgrade aborted without modifying report data"
        )
    op.drop_constraint("ck_export_p61_source", "export_reports", type_="check")
    op.create_check_constraint(
        "ck_export_p61_source",
        "export_reports",
        "source_snapshot IS NULL OR "
        "(report_type = 'MARKDOWN' AND (status = 'FAILED' OR content_hash IS NOT NULL))",
    )
