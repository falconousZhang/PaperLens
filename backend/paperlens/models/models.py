import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from paperlens.core.database import Base
from paperlens.core.enums import (
    PaperStatus,
    TaskStatus,
    EvidenceType,
    FindingType,
    VerificationStatus,
    ExportStatus,
    UserRole,
    UserStatus,
    CheckpointType,
    TaskType,
    ExperimentFileType,
    LearningMode,
    LearningScopeType,
    LearningStatus,
    QATurnStatus,
    ReadingStatus,
    HighlightColor,
    AnchorType,
    MasteryStatus,
)


def _enum_in_sql(enum_cls) -> str:
    return "(" + ", ".join(f"'{m}'" for m in enum_cls.__members__) + ")"


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    email_normalized: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="USER")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    password_changed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"role IN {_enum_in_sql(UserRole)}",
            name="ck_user_role_values",
        ),
        CheckConstraint(
            f"status IN {_enum_in_sql(UserStatus)}",
            name="ck_user_status_values",
        ),
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    sid: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    family_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    replaced_by_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("auth_sessions.sid", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("idx_auth_session_family", "family_id"),
        Index("idx_auth_session_user", "user_id"),
        Index("idx_auth_session_token_hash", "token_hash", unique=True),
        Index("idx_auth_session_expires_at", "expires_at"),
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_password_reset_user", "user_id"),
        Index("idx_password_reset_token_hash", "token_hash", unique=True),
        Index("idx_password_reset_expires_at", "expires_at"),
    )


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UPLOADING")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    pages: Mapped[list["PaperPage"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    sections: Mapped[list["PaperSection"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    chunks: Mapped[list["PaperChunk"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    tables: Mapped[list["PaperTable"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    learning_explanations: Mapped[list["LearningExplanation"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    qa_conversations: Mapped[list["PaperQAConversation"]] = relationship(back_populates="paper", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            f"status IN {_enum_in_sql(PaperStatus)}",
            name="ck_paper_status_values",
        ),
        Index("idx_paper_user_id", "user_id"),
        Index("idx_paper_file_hash", "file_hash"),
        Index("idx_paper_status", "status"),
    )


class PaperPage(Base):
    __tablename__ = "paper_pages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)

    paper: Mapped["Paper"] = relationship(back_populates="pages")

    __table_args__ = (
        CheckConstraint("page_number >= 1", name="ck_paper_page_number_gte1"),
        UniqueConstraint("paper_id", "page_number", name="uq_paper_page"),
    )


class PaperSection(Base):
    __tablename__ = "paper_sections"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    section_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    paper: Mapped["Paper"] = relationship(back_populates="sections")

    __table_args__ = (
        Index("idx_paper_section_paper_id", "paper_id", "sequence"),
    )


class PaperChunk(Base):
    __tablename__ = "paper_chunks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("paper_sections.id", ondelete="SET NULL"), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page_numbers: Mapped[list | None] = mapped_column(ARRAY(Integer), nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    paper: Mapped["Paper"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("paper_id", "chunk_index", name="uq_paper_chunk"),
    )


class PaperTable(Base):
    __tablename__ = "paper_tables"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    table_index: Mapped[int] = mapped_column(Integer, nullable=False)
    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bbox_x0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[float | None] = mapped_column(Float, nullable=True)
    structured_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    paper: Mapped["Paper"] = relationship(back_populates="tables")

    __table_args__ = (
        CheckConstraint("page_number >= 1", name="ck_paper_table_page_number_gte1"),
        CheckConstraint("table_index >= 1", name="ck_paper_table_table_index_gte1"),
        CheckConstraint("bbox_x1 >= bbox_x0", name="ck_paper_table_bbox_x_valid"),
        CheckConstraint("bbox_y1 >= bbox_y0", name="ck_paper_table_bbox_y_valid"),
        UniqueConstraint("paper_id", "page_number", "table_index", name="uq_paper_table"),
    )


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("paper_chunks.id", ondelete="SET NULL"), nullable=True)
    section_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("paper_sections.id", ondelete="SET NULL"), nullable=True)
    quoted_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_x0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[float | None] = mapped_column(Float, nullable=True)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    paper: Mapped["Paper"] = relationship(back_populates="evidences")

    __table_args__ = (
        CheckConstraint("page_number >= 1", name="ck_evidence_page_number_gte1"),
        CheckConstraint("char_start >= 0", name="ck_evidence_char_start_gte0"),
        CheckConstraint("char_end >= char_start", name="ck_evidence_char_end_gte_char_start"),
        CheckConstraint("bbox_x1 >= bbox_x0", name="ck_evidence_bbox_x_valid"),
        CheckConstraint("bbox_y1 >= bbox_y0", name="ck_evidence_bbox_y_valid"),
        CheckConstraint(
            f"evidence_type IN {_enum_in_sql(EvidenceType)}",
            name="ck_evidence_type_values",
        ),
        Index("idx_evidence_paper_id", "paper_id"),
        Index("idx_evidence_chunk_id", "chunk_id"),
        Index("idx_evidence_page", "paper_id", "page_number"),
    )


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    experiment_file_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("experiment_files.id", ondelete="RESTRICT"), nullable=True
    )

    review_results: Mapped[list["ReviewResult"]] = relationship(back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            f"task_type IN {_enum_in_sql(TaskType)}",
            name="ck_analysis_task_type_values",
        ),
        CheckConstraint(
            f"status IN {_enum_in_sql(TaskStatus)}",
            name="ck_analysis_task_status_values",
        ),
        CheckConstraint("progress BETWEEN 0 AND 100", name="ck_analysis_task_progress_range"),
        CheckConstraint(
            "(task_type = 'EXPERIMENT_ANALYSIS') = (experiment_file_id IS NOT NULL)",
            name="ck_experiment_analysis_has_file_id",
        ),
        Index("idx_task_paper_id", "paper_id"),
        Index("idx_task_status", "status"),
        Index("idx_task_user_id", "user_id"),
        Index("idx_task_experiment_file_id", "experiment_file_id"),
        Index(
            "uq_active_metric_task_per_user_paper",
            "user_id",
            "paper_id",
            unique=True,
            postgresql_where=text(
                "task_type = 'METRIC_EXTRACTION' AND status IN ('PENDING', 'RUNNING')"
            ),
        ),
        Index(
            "uq_active_experiment_task_per_user_file",
            "user_id",
            "experiment_file_id",
            unique=True,
            postgresql_where=text(
                "task_type = 'EXPERIMENT_ANALYSIS' AND status IN ('PENDING', 'RUNNING')"
            ),
        ),
    )


class ReviewResult(Base):
    __tablename__ = "review_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    dimension: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    task: Mapped["AnalysisTask"] = relationship(back_populates="review_results")
    findings: Mapped[list["ReviewFinding"]] = relationship(back_populates="review", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating_range"),
        Index("idx_review_task_id", "task_id"),
        Index("idx_review_paper_id", "paper_id"),
        UniqueConstraint("task_id", "dimension", name="uq_review_dimension"),
    )


class ReviewFinding(Base):
    __tablename__ = "review_findings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    review_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("review_results.id", ondelete="CASCADE"), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    review: Mapped["ReviewResult"] = relationship(back_populates="findings")
    evidences: Mapped[list["Evidence"]] = relationship(
        secondary="finding_evidences",
        backref="findings",
    )

    __table_args__ = (
        CheckConstraint(
            f"finding_type IN {_enum_in_sql(FindingType)}",
            name="ck_finding_type_values",
        ),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_finding_confidence_range"),
        CheckConstraint(
            f"verification_status IN {_enum_in_sql(VerificationStatus)}",
            name="ck_verification_status_values",
        ),
        Index("idx_finding_review_id", "review_id", "sequence"),
        Index("idx_finding_type", "review_id", "finding_type"),
    )


class FindingEvidence(Base):
    __tablename__ = "finding_evidences"

    finding_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("review_findings.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    evidence_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )


class MetricRecord(Base):
    __tablename__ = "metric_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dataset_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    checkpoint_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CheckpointType.UNKNOWN
    )
    checkpoint_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("evidences.id", ondelete="RESTRICT"), nullable=True
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    table_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("paper_tables.id", ondelete="RESTRICT"), nullable=True
    )
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            f"checkpoint_type IN {_enum_in_sql(CheckpointType)}",
            name="ck_metric_checkpoint_type_values",
        ),
        CheckConstraint(
            "metric_value > '-Infinity'::float8 AND metric_value < 'Infinity'::float8",
            name="ck_metric_value_finite",
        ),
        CheckConstraint(
            "(table_id IS NOT NULL AND evidence_id IS NULL AND row_index IS NOT NULL AND row_index >= 0) "
            "OR (table_id IS NULL AND evidence_id IS NOT NULL AND row_index IS NULL)",
            name="ck_metric_exactly_one_source",
        ),
        Index("idx_metric_paper_id", "paper_id"),
        Index("idx_metric_task_id", "task_id"),
        Index("idx_metric_user_id", "user_id"),
        Index("idx_metric_name", "metric_name"),
        Index("idx_metric_checkpoint_type", "checkpoint_type"),
    )


class ExperimentFile(Base):
    __tablename__ = "experiment_files"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False)
    columns_info: Mapped[dict] = mapped_column(JSONB, nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    result: Mapped["ExperimentResult | None"] = relationship(back_populates="file", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            f"file_type IN {_enum_in_sql(ExperimentFileType)}",
            name="ck_exp_file_type_values",
        ),
        CheckConstraint("file_size > 0", name="ck_exp_file_size_positive"),
        CheckConstraint(
            "file_hash ~ '^[0-9a-f]{64}$'",
            name="ck_exp_file_hash_hex64",
        ),
        CheckConstraint("row_count >= 1 AND row_count <= 100000", name="ck_exp_file_row_count_range"),
        CheckConstraint("column_count >= 1 AND column_count <= 256", name="ck_exp_file_column_count_range"),
        UniqueConstraint("user_id", "paper_id", "file_hash", name="uq_exp_file_user_paper_hash"),
        Index("idx_exp_file_paper_id", "paper_id"),
        Index("idx_exp_file_user_id", "user_id"),
    )


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    file_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("experiment_files.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False)
    summary_stats: Mapped[dict] = mapped_column(JSONB, nullable=False)
    column_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metric_comparisons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    file: Mapped["ExperimentFile"] = relationship(back_populates="result")


class ExportReport(Base):
    __tablename__ = "export_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False, default="zh")
    include_metrics: Mapped[bool] = mapped_column(default=True, nullable=False)
    include_experiment_analysis: Mapped[bool] = mapped_column(default=True, nullable=False)
    source_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"status IN {_enum_in_sql(ExportStatus)}",
            name="ck_export_status_values",
        ),
        CheckConstraint(
            "report_type IN ('MARKDOWN', 'PDF', 'DOCX')",
            name="ck_export_report_type_values",
        ),
        CheckConstraint(
            "language IN ('zh', 'en')",
            name="ck_export_language_values",
        ),
        CheckConstraint(
            "source_snapshot IS NULL OR ((status = 'READY') = "
            "(storage_key IS NOT NULL AND file_size IS NOT NULL AND completed_at IS NOT NULL))",
            name="ck_export_ready_has_storage",
        ),
        CheckConstraint(
            "source_snapshot IS NULL OR ((status = 'FAILED') = (error_message IS NOT NULL))",
            name="ck_export_failed_has_error",
        ),
        CheckConstraint(
            "(source_snapshot IS NULL) = (source_hash IS NULL)",
            name="ck_export_source_pair",
        ),
        CheckConstraint(
            "source_hash IS NULL OR source_hash ~ '^[0-9a-f]{64}$'",
            name="ck_export_source_hash_hex64",
        ),
        CheckConstraint(
            "content_hash IS NULL OR content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_export_content_hash_hex64",
        ),
        CheckConstraint(
            "source_snapshot IS NULL OR "
            "(report_type IN ('MARKDOWN', 'PDF', 'DOCX') AND (status = 'FAILED' OR content_hash IS NOT NULL))",
            name="ck_export_p61_source",
        ),
        CheckConstraint(
            "source_snapshot IS NULL OR status = 'READY' OR "
            "(storage_key IS NULL AND file_size IS NULL)",
            name="ck_export_nonready_no_storage",
        ),
        CheckConstraint(
            "source_snapshot IS NULL OR "
            "((status IN ('READY', 'FAILED')) = (completed_at IS NOT NULL))",
            name="ck_export_completed_terminal",
        ),
        CheckConstraint(
            "file_size IS NULL OR file_size >= 0",
            name="ck_export_file_size_nonneg",
        ),
        Index("idx_export_paper_id", "paper_id"),
        Index("idx_export_user_id", "user_id"),
        Index("idx_export_status", "status"),
        Index(
            "uq_active_export_source",
            "user_id",
            "paper_id",
            "report_type",
            "language",
            "include_metrics",
            "include_experiment_analysis",
            "source_hash",
            "content_hash",
            unique=True,
            postgresql_where=text(
                "source_hash IS NOT NULL AND content_hash IS NOT NULL "
                "AND status IN ('PENDING', 'GENERATING', 'READY')"
            ),
        ),
    )


class LearningExplanation(Base):
    __tablename__ = "learning_explanations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    output_language: Mapped[str] = mapped_column(String(2), nullable=False)
    section_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("paper_sections.id", ondelete="CASCADE"), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("evidences.id", ondelete="CASCADE"), nullable=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    terms: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    paper: Mapped["Paper"] = relationship(back_populates="learning_explanations")
    citations: Mapped[list["LearningCitation"]] = relationship(back_populates="explanation", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            f"mode IN {_enum_in_sql(LearningMode)}",
            name="ck_learning_mode_values",
        ),
        CheckConstraint(
            f"scope_type IN {_enum_in_sql(LearningScopeType)}",
            name="ck_learning_scope_type_values",
        ),
        CheckConstraint(
            "output_language IN ('zh', 'en')",
            name="ck_learning_output_language_values",
        ),
        CheckConstraint(
            f"status IN {_enum_in_sql(LearningStatus)}",
            name="ck_learning_status_values",
        ),
        CheckConstraint(
            "(scope_type = 'SECTION' AND section_id IS NOT NULL AND page_number IS NULL AND evidence_id IS NULL) OR "
            "(scope_type = 'PAGE' AND section_id IS NULL AND page_number IS NOT NULL AND page_number >= 1 AND evidence_id IS NULL) OR "
            "(scope_type = 'EVIDENCE' AND section_id IS NULL AND page_number IS NULL AND evidence_id IS NOT NULL)",
            name="ck_learning_scope_exclusive",
        ),
        CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_learning_request_hash_hex64",
        ),
        CheckConstraint(
            "status = 'PENDING' AND answer IS NULL AND key_points IS NULL AND terms IS NULL AND error_message IS NULL AND started_at IS NULL AND completed_at IS NULL OR "
            "status != 'PENDING'",
            name="ck_learning_pending_no_result",
        ),
        CheckConstraint(
            "(status = 'RUNNING') = (started_at IS NOT NULL AND answer IS NULL AND key_points IS NULL AND terms IS NULL AND error_message IS NULL AND completed_at IS NULL)",
            name="ck_learning_running_state",
        ),
        CheckConstraint(
            "(status = 'SUCCEEDED') = (started_at IS NOT NULL AND completed_at IS NOT NULL AND length(btrim(answer)) > 0 AND jsonb_typeof(key_points) = 'array' AND jsonb_array_length(key_points) > 0 AND jsonb_typeof(terms) = 'array' AND jsonb_array_length(terms) > 0 AND error_message IS NULL)",
            name="ck_learning_succeeded_state",
        ),
        CheckConstraint(
            "(status = 'FAILED') = (started_at IS NOT NULL AND completed_at IS NOT NULL AND error_message = '学习解释生成失败，请稍后重试' AND answer IS NULL AND key_points IS NULL AND terms IS NULL)",
            name="ck_learning_failed_state",
        ),
        Index("idx_learning_user_paper", "user_id", "paper_id"),
        Index("idx_learning_paper_created", "paper_id", created_at.desc(), id.desc()),
        Index("idx_learning_status", "status"),
        Index(
            "uq_active_learning_request",
            "user_id",
            "paper_id",
            "request_hash",
            unique=True,
            postgresql_where=text(
                "status IN ('PENDING', 'RUNNING', 'SUCCEEDED')"
            ),
        ),
    )


class LearningCitation(Base):
    __tablename__ = "learning_citations"

    explanation_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("learning_explanations.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    evidence_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("evidences.id", ondelete="RESTRICT"), nullable=False, primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    explanation: Mapped["LearningExplanation"] = relationship(back_populates="citations")
    evidence: Mapped["Evidence"] = relationship()

    __table_args__ = (
        CheckConstraint("sequence >= 1", name="ck_learning_citation_sequence_positive"),
        UniqueConstraint("explanation_id", "sequence", name="uq_learning_citation_sequence"),
        Index("idx_learning_citation_evidence", "evidence_id"),
    )


class PaperQAConversation(Base):
    __tablename__ = "paper_qa_conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    paper: Mapped["Paper"] = relationship(back_populates="qa_conversations")
    turns: Mapped[list["PaperQATurn"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_qa_conv_user_paper", "user_id", "paper_id"),
        Index("idx_qa_conv_paper_updated", "paper_id", updated_at.desc(), id.desc()),
    )


class PaperQATurn(Base):
    __tablename__ = "paper_qa_turns"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("paper_qa_conversations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    paper_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    client_request_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    output_language: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    grounded: Mapped[bool | None] = mapped_column(default=None, nullable=True)
    context_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conversation: Mapped["PaperQAConversation"] = relationship(back_populates="turns")
    citations: Mapped[list["PaperQACitation"]] = relationship(back_populates="turn", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            f"status IN {_enum_in_sql(QATurnStatus)}",
            name="ck_qa_turn_status_values",
        ),
        CheckConstraint("sequence >= 1", name="ck_qa_turn_sequence_positive"),
        CheckConstraint(
            "btrim(question) <> '' AND char_length(question) <= 2000",
            name="ck_qa_turn_question_valid",
        ),
        CheckConstraint(
            "output_language IN ('zh', 'en')",
            name="ck_qa_turn_output_language_values",
        ),
        CheckConstraint(
            "context_hash IS NULL OR context_hash ~ '^[0-9a-f]{64}$'",
            name="ck_qa_turn_context_hash_hex64",
        ),
        CheckConstraint(
            "(status = 'PENDING') = (context_hash IS NULL AND answer IS NULL "
            "AND grounded IS NULL AND error_message IS NULL AND started_at IS NULL "
            "AND completed_at IS NULL)",
            name="ck_qa_turn_pending_state",
        ),
        CheckConstraint(
            "(status = 'RUNNING') = (started_at IS NOT NULL AND answer IS NULL AND grounded IS NULL "
            "AND error_message IS NULL AND completed_at IS NULL)",
            name="ck_qa_turn_running_state",
        ),
        CheckConstraint(
            "(status = 'SUCCEEDED') = (started_at IS NOT NULL AND completed_at IS NOT NULL "
            "AND context_hash IS NOT NULL AND answer IS NOT NULL AND btrim(answer) <> '' "
            "AND grounded IS NOT NULL AND error_message IS NULL)",
            name="ck_qa_turn_succeeded_state",
        ),
        CheckConstraint(
            "(status = 'FAILED') = (started_at IS NOT NULL AND completed_at IS NOT NULL "
            "AND context_hash IS NULL AND answer IS NULL AND grounded IS NULL "
            "AND error_message = '论文问答生成失败，请稍后重试')",
            name="ck_qa_turn_failed_state",
        ),

        UniqueConstraint("conversation_id", "sequence", name="uq_qa_turn_conv_sequence"),
        UniqueConstraint("user_id", "conversation_id", "client_request_id", name="uq_qa_turn_client_request"),
        Index("idx_qa_turn_conversation", "conversation_id", "sequence"),
        Index(
            "uq_qa_turn_active_conversation",
            "conversation_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'RUNNING')"),
        ),
    )


class PaperQACitation(Base):
    __tablename__ = "paper_qa_citations"

    turn_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("paper_qa_turns.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    evidence_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("evidences.id", ondelete="RESTRICT"), nullable=False, primary_key=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    turn: Mapped["PaperQATurn"] = relationship(back_populates="citations")
    evidence: Mapped["Evidence"] = relationship()

    __table_args__ = (
        CheckConstraint("sequence >= 1", name="ck_qa_citation_sequence_positive"),
        UniqueConstraint("turn_id", "sequence", name="uq_qa_citation_sequence"),
        Index("idx_qa_citation_evidence", "evidence_id"),
    )


class PaperLibraryEntry(Base):
    __tablename__ = "paper_library_entries"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, primary_key=True)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    reading_status: Mapped[str] = mapped_column(String(20), nullable=False, default="TO_READ")
    favorite: Mapped[bool] = mapped_column(default=False, nullable=False)
    collection_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    furthest_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_read_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            f"reading_status IN {_enum_in_sql(ReadingStatus)}",
            name="ck_library_reading_status_values",
        ),
        CheckConstraint(
            "collection_name IS NULL OR (collection_name = btrim(collection_name) AND char_length(collection_name) BETWEEN 1 AND 100)",
            name="ck_library_collection_name_trimmed",
        ),
        CheckConstraint(
            "last_page IS NULL OR last_page >= 1",
            name="ck_library_last_page_positive",
        ),
        CheckConstraint(
            "furthest_page IS NULL OR furthest_page >= 1",
            name="ck_library_furthest_page_positive",
        ),
        CheckConstraint(
            "last_page IS NULL OR furthest_page IS NULL OR last_page <= furthest_page",
            name="ck_library_last_le_furthest",
        ),
        CheckConstraint(
            "(reading_status = 'COMPLETED') = (completed_at IS NOT NULL)",
            name="ck_library_completed_has_date",
        ),
        Index("idx_library_user_status_favorite_collection", "user_id", "reading_status", "favorite", "collection_name"),
        Index("idx_library_user_last_read_paper", "user_id", text("last_read_at DESC"), text("paper_id DESC")),
    )


class PaperHighlight(Base):
    __tablename__ = "paper_highlights"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    quoted_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="YELLOW")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("page_number >= 1", name="ck_highlight_page_positive"),
        CheckConstraint("char_start >= 0", name="ck_highlight_char_start_nonneg"),
        CheckConstraint("char_end > char_start", name="ck_highlight_char_end_gt_start"),
        CheckConstraint(
            "char_length(quoted_text) <= 5000 AND char_length(btrim(quoted_text)) >= 1",
            name="ck_highlight_quoted_text_valid",
        ),
        CheckConstraint(
            f"color IN {_enum_in_sql(HighlightColor)}",
            name="ck_highlight_color_values",
        ),
        CheckConstraint(
            "source_hash ~ '^[0-9a-f]{64}$'",
            name="ck_highlight_source_hash_hex64",
        ),
        UniqueConstraint("user_id", "paper_id", "page_number", "char_start", "char_end", name="uq_highlight_user_paper_range"),
        Index("idx_highlight_user_paper_page_range", "user_id", "paper_id", "page_number", "char_start", "id"),
    )


class PaperBookmark(Base):
    __tablename__ = "paper_bookmarks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("page_number >= 1", name="ck_bookmark_page_positive"),
        CheckConstraint(
            "label IS NULL OR (label = btrim(label) AND char_length(label) BETWEEN 1 AND 100)",
            name="ck_bookmark_label_trimmed",
        ),
        UniqueConstraint("user_id", "paper_id", "page_number", name="uq_bookmark_user_paper_page"),
        Index("idx_bookmark_user_paper_page_id", "user_id", "paper_id", "page_number", "id"),
    )


class PaperNote(Base):
    __tablename__ = "paper_notes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    anchor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    highlight_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("paper_highlights.id", ondelete="RESTRICT"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            f"anchor_type IN {_enum_in_sql(AnchorType)}",
            name="ck_note_anchor_type_values",
        ),
        CheckConstraint("page_number IS NULL OR page_number >= 1", name="ck_note_page_positive"),
        CheckConstraint(
            "content = btrim(content) AND char_length(content) BETWEEN 1 AND 20000",
            name="ck_note_content_valid",
        ),
        CheckConstraint(
            "(anchor_type = 'PAPER' AND page_number IS NULL AND highlight_id IS NULL) OR "
            "(anchor_type = 'PAGE' AND page_number IS NOT NULL AND highlight_id IS NULL) OR "
            "(anchor_type = 'HIGHLIGHT' AND page_number IS NULL AND highlight_id IS NOT NULL)",
            name="ck_note_anchor_exclusive",
        ),
        Index("idx_note_user_paper_created_id", "user_id", "paper_id", text("created_at DESC"), text("id DESC")),
        Index("idx_note_user_paper_anchor", "user_id", "paper_id", "anchor_type", "page_number", "highlight_id"),
    )


class PaperKnowledgeCard(Base):
    __tablename__ = "paper_knowledge_cards"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    paper_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    source_note_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("paper_notes.id", ondelete="RESTRICT"), nullable=True)
    source_highlight_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("paper_highlights.id", ondelete="RESTRICT"), nullable=True)
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    mastery_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    last_reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            f"mastery_status IN {_enum_in_sql(MasteryStatus)}",
            name="ck_card_mastery_status_values",
        ),
        CheckConstraint(
            "front = btrim(front) AND char_length(front) BETWEEN 1 AND 2000",
            name="ck_card_front_valid",
        ),
        CheckConstraint(
            "back = btrim(back) AND char_length(back) BETWEEN 1 AND 10000",
            name="ck_card_back_valid",
        ),
        CheckConstraint(
            "NOT (source_note_id IS NOT NULL AND source_highlight_id IS NOT NULL)",
            name="ck_card_source_exclusive",
        ),
        Index("idx_card_user_paper_updated_id", "user_id", "paper_id", text("updated_at DESC"), text("id DESC")),
        Index("idx_card_user_paper_mastery_archived", "user_id", "paper_id", "mastery_status", "archived"),
    )


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    actor_user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    before_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    after_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "action IN ('ADMIN_BOOTSTRAPPED', 'USER_ROLE_CHANGED', 'USER_STATUS_CHANGED')",
            name="ck_audit_action_whitelist",
        ),
        CheckConstraint(
            "resource_type = 'USER'",
            name="ck_audit_resource_type_user",
        ),
        CheckConstraint(
            "char_length(reason) BETWEEN 8 AND 500",
            name="ck_audit_reason_length",
        ),
        CheckConstraint(
            "reason ~ '^[^\\x00-\\x1f]+$'",
            name="ck_audit_reason_no_control_chars",
        ),
        CheckConstraint(
            "jsonb_typeof(before_state) = 'object'",
            name="ck_audit_before_state_is_object",
        ),
        CheckConstraint(
            "jsonb_typeof(after_state) = 'object'",
            name="ck_audit_after_state_is_object",
        ),
        Index("idx_audit_actor", "actor_user_id"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created", text("created_at DESC"), text("id DESC")),
    )
