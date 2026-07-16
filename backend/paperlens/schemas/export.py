from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, UUID4, Field

from paperlens.core.enums import ExportStatus


class CreateExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_type: Literal["MARKDOWN", "PDF", "DOCX"]
    language: Literal["zh", "en"] = "zh"
    include_metrics: bool = True
    include_experiment_analysis: bool = True


class ExportReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    paper_id: UUID4
    report_type: Literal["MARKDOWN", "PDF", "DOCX"]
    language: Literal["zh", "en"]
    include_metrics: bool
    include_experiment_analysis: bool
    status: ExportStatus
    file_size: int | None
    error_message: Literal["报告生成失败，请稍后重试"] | None
    created_at: datetime.datetime
    completed_at: datetime.datetime | None
    duplicate: bool


class ExportListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    paper_id: UUID4
    report_type: Literal["MARKDOWN", "PDF", "DOCX"]
    language: Literal["zh", "en"]
    include_metrics: bool
    include_experiment_analysis: bool
    status: ExportStatus
    file_size: int | None
    error_message: Literal["报告生成失败，请稍后重试"] | None
    created_at: datetime.datetime
    completed_at: datetime.datetime | None


class ExportListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ExportListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
