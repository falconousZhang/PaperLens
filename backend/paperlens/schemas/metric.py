from __future__ import annotations

import datetime

from pydantic import UUID4, BaseModel, ConfigDict, Field

from paperlens.core.enums import CheckpointType


class MetricRecordResponse(BaseModel):
    id: str
    paper_id: str
    task_id: str
    model_name: str | None
    dataset_name: str | None
    metric_name: str
    metric_value: float
    checkpoint_type: CheckpointType
    checkpoint_source: str | None
    evidence_id: str | None
    table_id: str | None
    row_index: int | None
    raw_text: str
    created_at: datetime.datetime


class MetricListResponse(BaseModel):
    items: list[MetricRecordResponse]
    total: int
    page: int
    page_size: int


class MetricExtractionOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MetricListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    task_id: UUID4 | None = None
    metric_name: str | None = Field(default=None, min_length=1, max_length=100)
    dataset_name: str | None = Field(default=None, min_length=1, max_length=200)
    checkpoint_type: CheckpointType | None = None
