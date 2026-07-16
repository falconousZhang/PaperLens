"""export report p61 integrity

Revision ID: 011_export_report_p61_integrity
Revises: 010_export_report_p61
Create Date: 2026-07-15
"""

import datetime
import hashlib
import json

from alembic import op
import sqlalchemy as sa


revision = "011_export_report_p61_integrity"
down_revision = "010_export_report_p61"
branch_labels = None
depends_on = None


def _source_hash(value: dict) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def upgrade() -> None:
    op.add_column(
        "export_reports",
        sa.Column("source_hash", sa.String(64), nullable=True),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, source_snapshot, status FROM export_reports "
            "WHERE source_snapshot IS NOT NULL"
        )
    ).mappings()
    now = datetime.datetime.now(datetime.timezone.utc)
    for row in rows:
        values: dict[str, object] = {"source_hash": _source_hash(row["source_snapshot"])}
        if row["status"] in {"PENDING", "GENERATING"}:
            values.update(
                status="FAILED",
                storage_key=None,
                file_size=None,
                error_message="报告生成失败，请稍后重试",
                completed_at=now,
            )
        bind.execute(
            sa.text(
                "UPDATE export_reports SET source_hash = :source_hash, status = COALESCE(:status, status), "
                "storage_key = CASE WHEN :status IS NULL THEN storage_key ELSE NULL END, "
                "file_size = CASE WHEN :status IS NULL THEN file_size ELSE NULL END, "
                "error_message = CASE WHEN :status IS NULL THEN error_message ELSE :error_message END, "
                "completed_at = CASE WHEN :status IS NULL THEN completed_at ELSE :completed_at END "
                "WHERE id = :id"
            ),
            {
                "id": row["id"],
                "source_hash": values["source_hash"],
                "status": values.get("status"),
                "error_message": values.get("error_message"),
                "completed_at": values.get("completed_at"),
            },
        )
    bind.execute(
        sa.text(
            "UPDATE export_reports "
            "SET completed_at = COALESCE(completed_at, created_at, :completed_at) "
            "WHERE source_snapshot IS NOT NULL AND status IN ('READY', 'FAILED')"
        ),
        {"completed_at": now},
    )

    op.execute(sa.text("DROP INDEX IF EXISTS uq_active_export_per_user_paper_type_lang"))
    op.drop_constraint("ck_export_report_type_markdown", "export_reports", type_="check")
    op.drop_constraint("ck_export_ready_has_storage", "export_reports", type_="check")
    op.drop_constraint("ck_export_failed_has_error", "export_reports", type_="check")

    op.create_check_constraint(
        "ck_export_report_type_values",
        "export_reports",
        "report_type IN ('MARKDOWN', 'PDF', 'DOCX')",
    )
    op.create_check_constraint(
        "ck_export_ready_has_storage",
        "export_reports",
        "source_snapshot IS NULL OR ((status = 'READY') = "
        "(storage_key IS NOT NULL AND file_size IS NOT NULL AND completed_at IS NOT NULL))",
    )
    op.create_check_constraint(
        "ck_export_failed_has_error",
        "export_reports",
        "source_snapshot IS NULL OR ((status = 'FAILED') = (error_message IS NOT NULL))",
    )
    op.create_check_constraint(
        "ck_export_source_pair",
        "export_reports",
        "(source_snapshot IS NULL) = (source_hash IS NULL)",
    )
    op.create_check_constraint(
        "ck_export_source_hash_hex64",
        "export_reports",
        "source_hash IS NULL OR source_hash ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_export_content_hash_hex64",
        "export_reports",
        "content_hash IS NULL OR content_hash ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_export_p61_source",
        "export_reports",
        "source_snapshot IS NULL OR "
        "(report_type = 'MARKDOWN' AND (status = 'FAILED' OR content_hash IS NOT NULL))",
    )
    op.create_check_constraint(
        "ck_export_nonready_no_storage",
        "export_reports",
        "source_snapshot IS NULL OR status = 'READY' OR "
        "(storage_key IS NULL AND file_size IS NULL)",
    )
    op.create_check_constraint(
        "ck_export_completed_terminal",
        "export_reports",
        "source_snapshot IS NULL OR "
        "((status IN ('READY', 'FAILED')) = (completed_at IS NOT NULL))",
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_active_export_source
            ON export_reports (
                user_id, paper_id, report_type, language,
                include_metrics, include_experiment_analysis,
                source_hash, content_hash
            )
            WHERE source_hash IS NOT NULL AND content_hash IS NOT NULL
              AND status IN ('PENDING', 'GENERATING', 'READY')
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    has_p61_data = bind.execute(
        sa.text("SELECT count(*) FROM export_reports WHERE source_hash IS NOT NULL")
    ).scalar_one()
    if has_p61_data > 0:
        raise RuntimeError(
            "P6.1 export reports exist; downgrade aborted without modifying report data"
        )

    op.execute(sa.text("DROP INDEX IF EXISTS uq_active_export_source"))
    op.drop_constraint("ck_export_completed_terminal", "export_reports", type_="check")
    op.drop_constraint("ck_export_nonready_no_storage", "export_reports", type_="check")
    op.drop_constraint("ck_export_p61_source", "export_reports", type_="check")
    op.drop_constraint("ck_export_content_hash_hex64", "export_reports", type_="check")
    op.drop_constraint("ck_export_source_hash_hex64", "export_reports", type_="check")
    op.drop_constraint("ck_export_source_pair", "export_reports", type_="check")
    op.drop_constraint("ck_export_failed_has_error", "export_reports", type_="check")
    op.drop_constraint("ck_export_ready_has_storage", "export_reports", type_="check")
    op.drop_constraint("ck_export_report_type_values", "export_reports", type_="check")
    op.drop_column("export_reports", "source_hash")

    op.create_check_constraint(
        "ck_export_report_type_markdown",
        "export_reports",
        "report_type IN ('MARKDOWN', 'PDF', 'DOCX')",
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
