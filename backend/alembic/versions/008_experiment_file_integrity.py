"""experiment file integrity constraints

Revision ID: 008_experiment_file_integrity
Revises: 007_metric_integrity_corrections
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "008_experiment_file_integrity"
down_revision = "007_metric_integrity_corrections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    invalid_count = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM experiment_files
            WHERE row_count IS NULL
               OR column_count IS NULL
               OR columns_info IS NULL
               OR jsonb_typeof(columns_info) <> 'object'
               OR file_type NOT IN ('CSV', 'XLSX', 'XLS')
               OR file_size <= 0
               OR file_hash !~ '^[0-9a-f]{64}$'
               OR row_count < 1 OR row_count > 100000
               OR column_count < 1 OR column_count > 256
            """
        )
    ).scalar_one()
    duplicate_count = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM (
                SELECT user_id, paper_id, file_hash
                FROM experiment_files
                GROUP BY user_id, paper_id, file_hash
                HAVING count(*) > 1
            ) AS duplicates
            """
        )
    ).scalar_one()
    if invalid_count or duplicate_count:
        raise RuntimeError(
            "experiment_files contains data incompatible with revision 008; "
            "migration aborted without modifying user data"
        )

    op.alter_column("experiment_files", "row_count", nullable=False)
    op.alter_column("experiment_files", "column_count", nullable=False)
    op.alter_column("experiment_files", "columns_info", nullable=False)

    op.create_check_constraint(
        "ck_exp_file_type_values",
        "experiment_files",
        "file_type IN ('CSV', 'XLSX', 'XLS')",
    )
    op.create_check_constraint(
        "ck_exp_file_size_positive",
        "experiment_files",
        "file_size > 0",
    )
    op.create_check_constraint(
        "ck_exp_file_hash_hex64",
        "experiment_files",
        "file_hash ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_exp_file_row_count_range",
        "experiment_files",
        "row_count >= 1 AND row_count <= 100000",
    )
    op.create_check_constraint(
        "ck_exp_file_column_count_range",
        "experiment_files",
        "column_count >= 1 AND column_count <= 256",
    )
    op.create_unique_constraint(
        "uq_exp_file_user_paper_hash",
        "experiment_files",
        ["user_id", "paper_id", "file_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_exp_file_user_paper_hash", "experiment_files", type_="unique"
    )
    op.drop_constraint(
        "ck_exp_file_column_count_range", "experiment_files", type_="check"
    )
    op.drop_constraint(
        "ck_exp_file_row_count_range", "experiment_files", type_="check"
    )
    op.drop_constraint(
        "ck_exp_file_hash_hex64", "experiment_files", type_="check"
    )
    op.drop_constraint(
        "ck_exp_file_size_positive", "experiment_files", type_="check"
    )
    op.drop_constraint(
        "ck_exp_file_type_values", "experiment_files", type_="check"
    )

    op.alter_column("experiment_files", "columns_info", nullable=True)
    op.alter_column("experiment_files", "column_count", nullable=True)
    op.alter_column("experiment_files", "row_count", nullable=True)
