"""add metric_records user_id, checkpoint_type constraint and metric_name index

Revision ID: 006_metric_user_and_constraints
Revises: 005_auth_security_corrections
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "006_metric_user_and_constraints"
down_revision = "005_auth_security_corrections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "metric_records",
        sa.Column("user_id", sa.String(length=128), nullable=True),
    )

    op.execute(
        "UPDATE metric_records SET user_id = analysis_tasks.user_id "
        "FROM analysis_tasks WHERE metric_records.task_id = analysis_tasks.id"
    )

    op.alter_column("metric_records", "user_id", nullable=False)

    op.create_foreign_key(
        "fk_metric_records_user_id",
        "metric_records",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index("idx_metric_user_id", "metric_records", ["user_id"])
    op.create_index("idx_metric_name", "metric_records", ["metric_name"])

    op.execute(
        "ALTER TABLE metric_records ADD CONSTRAINT ck_metric_checkpoint_type_values "
        "CHECK (checkpoint_type IN ('FINAL', 'MAX', 'MEAN', 'BEST', 'LAST', 'UNKNOWN'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE metric_records DROP CONSTRAINT ck_metric_checkpoint_type_values")

    op.drop_index("idx_metric_name", table_name="metric_records")
    op.drop_index("idx_metric_user_id", table_name="metric_records")

    op.drop_constraint("fk_metric_records_user_id", "metric_records", type_="foreignkey")

    op.drop_column("metric_records", "user_id")