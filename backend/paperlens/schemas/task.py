import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from paperlens.core.enums import (
    FindingType,
    OverallVerdict,
    ReviewDimension,
    TaskStatus,
    TaskType,
    VerificationStatus,
)
from paperlens.schemas.metric import MetricExtractionOptions


class TaskOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimensions: list[ReviewDimension] = Field(
        default_factory=lambda: [ReviewDimension.OVERALL],
        min_length=1,
        max_length=7,
    )
    language: Literal["zh", "en"] = "zh"

    @field_validator("dimensions")
    @classmethod
    def reject_duplicate_dimensions(cls, dimensions: list[ReviewDimension]) -> list[ReviewDimension]:
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("dimensions must not contain duplicates")
        return dimensions


class ReviewTaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: Literal[TaskType.REVIEW]
    options: TaskOptions | None = None


class MetricTaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: Literal[TaskType.METRIC_EXTRACTION]
    options: MetricExtractionOptions | None = None


class UnsupportedExperimentTaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: Literal[TaskType.EXPERIMENT_ANALYSIS]
    options: None = None


TaskCreateRequest = Annotated[
    ReviewTaskCreateRequest | MetricTaskCreateRequest | UnsupportedExperimentTaskCreateRequest,
    Field(discriminator="task_type"),
]


class TaskCreateResponse(BaseModel):
    id: str
    paper_id: str
    task_type: TaskType
    status: TaskStatus
    progress: int
    created_at: datetime.datetime


class TaskDetailResponse(BaseModel):
    id: str
    paper_id: str
    task_type: TaskType
    status: TaskStatus
    progress: int
    experiment_file_id: str | None
    error_message: str | None
    started_at: datetime.datetime | None
    completed_at: datetime.datetime | None
    created_at: datetime.datetime


class TaskListResponse(BaseModel):
    items: list[TaskDetailResponse]


class FindingResponse(BaseModel):
    id: str
    finding_type: FindingType
    content: str
    confidence: float | None
    verification_status: VerificationStatus
    sequence: int
    evidence_ids: list[str]


class ReviewResultResponse(BaseModel):
    id: str
    task_id: str
    dimension: ReviewDimension
    rating: int | None
    summary: str | None
    overall_verdict: OverallVerdict | None
    created_at: datetime.datetime
    findings: list[FindingResponse]


class ReviewListResponse(BaseModel):
    reviews: list[ReviewResultResponse]
