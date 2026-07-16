"""experiment analysis task link

Revision ID: 009_exp_analysis_task_link
Revises: 008_experiment_file_integrity
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "009_exp_analysis_task_link"
down_revision = "008_experiment_file_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    conflict_count = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM analysis_tasks
            WHERE task_type = 'EXPERIMENT_ANALYSIS'
            """
        )
    ).scalar_one()
    if conflict_count > 0:
        raise RuntimeError(
            "analysis_tasks contains EXPERIMENT_ANALYSIS records; "
            "migration aborted without modifying user data"
        )

    op.add_column(
        "analysis_tasks",
        sa.Column("experiment_file_id", sa.UUID(as_uuid=False), nullable=True),
    )

    op.create_foreign_key(
        "fk_analysis_task_experiment_file_id",
        "analysis_tasks",
        "experiment_files",
        ["experiment_file_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "idx_task_experiment_file_id",
        "analysis_tasks",
        ["experiment_file_id"],
    )

    op.create_check_constraint(
        "ck_experiment_analysis_has_file_id",
        "analysis_tasks",
        "(task_type = 'EXPERIMENT_ANALYSIS') = (experiment_file_id IS NOT NULL)",
    )

    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_active_experiment_task_per_user_file
            ON analysis_tasks (user_id, experiment_file_id)
            WHERE task_type = 'EXPERIMENT_ANALYSIS'
              AND status IN ('PENDING', 'RUNNING')
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    conflict_count = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM analysis_tasks
            WHERE task_type = 'EXPERIMENT_ANALYSIS'
               OR experiment_file_id IS NOT NULL
            """
        )
    ).scalar_one()
    if conflict_count > 0:
        raise RuntimeError(
            "analysis_tasks contains experiment analysis links; "
            "downgrade aborted without modifying user data"
        )
    op.execute(
        sa.text("DROP INDEX IF EXISTS uq_active_experiment_task_per_user_file")
    )
    op.drop_constraint(
        "ck_experiment_analysis_has_file_id", "analysis_tasks", type_="check"
    )
    op.drop_index("idx_task_experiment_file_id", table_name="analysis_tasks")
    op.drop_constraint(
        "fk_analysis_task_experiment_file_id", "analysis_tasks", type_="foreignkey"
    )
    op.drop_column("analysis_tasks", "experiment_file_id")
