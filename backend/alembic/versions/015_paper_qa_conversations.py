"""add paper qa conversations, turns, and citations

Revision ID: 015_paper_qa_conversations
Revises: 014_learning_contract_hardening
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "015_paper_qa_conversations"
down_revision = "014_learning_contract_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_qa_conversations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(128),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "paper_id",
            UUID(as_uuid=False),
            sa.ForeignKey("papers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_qa_conv_user_paper",
        "paper_qa_conversations",
        ["user_id", "paper_id"],
    )
    op.create_index(
        "idx_qa_conv_paper_updated",
        "paper_qa_conversations",
        ["paper_id", sa.text("updated_at DESC"), sa.text("id DESC")],
    )

    op.create_table(
        "paper_qa_turns",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "conversation_id",
            UUID(as_uuid=False),
            sa.ForeignKey("paper_qa_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(128),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "paper_id",
            UUID(as_uuid=False),
            sa.ForeignKey("papers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("client_request_id", UUID(as_uuid=False), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("output_language", sa.String(2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("context_hash", sa.String(64), nullable=True),
        sa.Column("answer", sa.Text, nullable=True),
        sa.Column("grounded", sa.Boolean, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_qa_turn_status_values",
        ),
        sa.CheckConstraint(
            "sequence >= 1",
            name="ck_qa_turn_sequence_positive",
        ),
        sa.CheckConstraint(
            "btrim(question) <> '' AND char_length(question) <= 2000",
            name="ck_qa_turn_question_valid",
        ),
        sa.CheckConstraint(
            "output_language IN ('zh', 'en')",
            name="ck_qa_turn_output_language_values",
        ),
        sa.CheckConstraint(
            "context_hash IS NULL OR context_hash ~ '^[0-9a-f]{64}$'",
            name="ck_qa_turn_context_hash_hex64",
        ),
        sa.CheckConstraint(
            "(status = 'PENDING') = (context_hash IS NULL AND answer IS NULL "
            "AND grounded IS NULL AND error_message IS NULL AND started_at IS NULL "
            "AND completed_at IS NULL)",
            name="ck_qa_turn_pending_state",
        ),
        sa.CheckConstraint(
            "(status = 'RUNNING') = (started_at IS NOT NULL AND answer IS NULL "
            "AND grounded IS NULL AND error_message IS NULL AND completed_at IS NULL)",
            name="ck_qa_turn_running_state",
        ),
        sa.CheckConstraint(
            "(status = 'SUCCEEDED') = (started_at IS NOT NULL AND completed_at IS NOT NULL "
            "AND context_hash IS NOT NULL AND answer IS NOT NULL AND btrim(answer) <> '' "
            "AND grounded IS NOT NULL AND error_message IS NULL)",
            name="ck_qa_turn_succeeded_state",
        ),
        sa.CheckConstraint(
            "(status = 'FAILED') = (started_at IS NOT NULL AND completed_at IS NOT NULL "
            "AND context_hash IS NULL AND answer IS NULL AND grounded IS NULL "
            "AND error_message = '论文问答生成失败，请稍后重试')",
            name="ck_qa_turn_failed_state",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "sequence",
            name="uq_qa_turn_conv_sequence",
        ),
        sa.UniqueConstraint(
            "user_id",
            "conversation_id",
            "client_request_id",
            name="uq_qa_turn_client_request",
        ),
    )
    op.create_index(
        "idx_qa_turn_conversation",
        "paper_qa_turns",
        ["conversation_id", "sequence"],
    )
    op.create_index(
        "uq_qa_turn_active_conversation",
        "paper_qa_turns",
        ["conversation_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'RUNNING')"),
    )

    op.create_table(
        "paper_qa_citations",
        sa.Column(
            "turn_id",
            UUID(as_uuid=False),
            sa.ForeignKey("paper_qa_turns.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "evidence_id",
            UUID(as_uuid=False),
            sa.ForeignKey("evidences.id", ondelete="RESTRICT"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.CheckConstraint(
            "sequence >= 1",
            name="ck_qa_citation_sequence_positive",
        ),
        sa.UniqueConstraint(
            "turn_id",
            "sequence",
            name="uq_qa_citation_sequence",
        ),
    )
    op.create_index(
        "idx_qa_citation_evidence",
        "paper_qa_citations",
        ["evidence_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    row_count = bind.execute(
        sa.text(
            "SELECT "
            "(SELECT count(*) FROM paper_qa_conversations) + "
            "(SELECT count(*) FROM paper_qa_turns) + "
            "(SELECT count(*) FROM paper_qa_citations)"
        )
    ).scalar_one()
    if row_count:
        raise RuntimeError("refusing to downgrade non-empty paper QA tables")
    op.drop_table("paper_qa_citations")
    op.drop_table("paper_qa_turns")
    op.drop_table("paper_qa_conversations")
