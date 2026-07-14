"""harden metric source, value and active task integrity

Revision ID: 007_metric_integrity_corrections
Revises: 006_metric_user_and_constraints
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "007_metric_integrity_corrections"
down_revision = "006_metric_user_and_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE metric_records SET checkpoint_type = 'UNKNOWN' "
        "WHERE checkpoint_type IS NULL"
    )
    op.alter_column("metric_records", "checkpoint_type", nullable=False)

    op.drop_constraint(
        "metric_records_evidence_id_fkey", "metric_records", type_="foreignkey"
    )
    op.drop_constraint(
        "metric_records_table_id_fkey", "metric_records", type_="foreignkey"
    )
    op.create_foreign_key(
        "metric_records_evidence_id_fkey",
        "metric_records",
        "evidences",
        ["evidence_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "metric_records_table_id_fkey",
        "metric_records",
        "paper_tables",
        ["table_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_check_constraint(
        "ck_analysis_task_type_values",
        "analysis_tasks",
        "task_type IN ('REVIEW', 'METRIC_EXTRACTION', 'EXPERIMENT_ANALYSIS')",
    )
    op.execute(
        "ALTER TABLE metric_records ADD CONSTRAINT ck_metric_value_finite "
        "CHECK (metric_value > '-Infinity'::float8 "
        "AND metric_value < 'Infinity'::float8) NOT VALID"
    )
    op.execute(
        "ALTER TABLE metric_records ADD CONSTRAINT ck_metric_exactly_one_source "
        "CHECK ((table_id IS NOT NULL AND evidence_id IS NULL "
        "AND row_index IS NOT NULL AND row_index >= 0) "
        "OR (table_id IS NULL AND evidence_id IS NOT NULL "
        "AND row_index IS NULL)) NOT VALID"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM metric_records "
        "WHERE NOT (metric_value > '-Infinity'::float8 "
        "AND metric_value < 'Infinity'::float8)) THEN "
        "ALTER TABLE metric_records VALIDATE CONSTRAINT ck_metric_value_finite; "
        "END IF; "
        "IF NOT EXISTS (SELECT 1 FROM metric_records "
        "WHERE NOT ((table_id IS NOT NULL AND evidence_id IS NULL "
        "AND row_index IS NOT NULL AND row_index >= 0) "
        "OR (table_id IS NULL AND evidence_id IS NOT NULL "
        "AND row_index IS NULL))) THEN "
        "ALTER TABLE metric_records VALIDATE CONSTRAINT ck_metric_exactly_one_source; "
        "END IF; END $$"
    )
    op.create_index(
        "uq_active_metric_task_per_user_paper",
        "analysis_tasks",
        ["user_id", "paper_id"],
        unique=True,
        postgresql_where=sa.text(
            "task_type = 'METRIC_EXTRACTION' "
            "AND status IN ('PENDING', 'RUNNING')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_active_metric_task_per_user_paper", table_name="analysis_tasks"
    )
    op.drop_constraint(
        "ck_metric_exactly_one_source", "metric_records", type_="check"
    )
    op.drop_constraint("ck_metric_value_finite", "metric_records", type_="check")
    op.drop_constraint(
        "ck_analysis_task_type_values", "analysis_tasks", type_="check"
    )

    op.drop_constraint(
        "metric_records_table_id_fkey", "metric_records", type_="foreignkey"
    )
    op.drop_constraint(
        "metric_records_evidence_id_fkey", "metric_records", type_="foreignkey"
    )
    op.create_foreign_key(
        "metric_records_table_id_fkey",
        "metric_records",
        "paper_tables",
        ["table_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "metric_records_evidence_id_fkey",
        "metric_records",
        "evidences",
        ["evidence_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("metric_records", "checkpoint_type", nullable=True)
