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
        Index("idx_task_paper_id", "paper_id"),
        Index("idx_task_status", "status"),
        Index("idx_task_user_id", "user_id"),
        Index(
            "uq_active_metric_task_per_user_paper",
            "user_id",
            "paper_id",
            unique=True,
            postgresql_where=text(
                "task_type = 'METRIC_EXTRACTION' AND status IN ('PENDING', 'RUNNING')"
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
        Index("idx_export_paper_id", "paper_id"),
        Index("idx_export_user_id", "user_id"),
        Index("idx_export_status", "status"),
    )
