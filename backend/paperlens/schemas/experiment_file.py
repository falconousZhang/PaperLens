from __future__ import annotations

import datetime
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, UUID4, field_validator, model_validator

from paperlens.core.enums import CheckpointType, ExperimentFileType, TaskStatus, TaskType


ColumnDtype = Literal["integer", "float", "boolean", "datetime", "string", "empty"]
CsvEncoding = Literal["utf-8", "utf-8-sig", "gb18030"]
CsvDelimiter = Literal[",", ";", "\t"]


class ExperimentColumnInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    dtype: ColumnDtype
    nullable: bool
    null_count: int = Field(ge=0, le=100000)


class ExperimentColumnsInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    encoding: CsvEncoding | None
    delimiter: CsvDelimiter | None
    sheet_name: str | None = Field(default=None, min_length=1, max_length=128)
    columns: list[ExperimentColumnInfo] = Field(min_length=1, max_length=256)


class ExperimentFileMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    paper_id: str
    filename: str = Field(min_length=1, max_length=255)
    file_type: ExperimentFileType
    file_size: int = Field(ge=1)
    row_count: int = Field(ge=1, le=100000)
    column_count: int = Field(ge=1, le=256)
    columns_info: ExperimentColumnsInfo
    created_at: datetime.datetime

    @model_validator(mode="after")
    def validate_structure(self):
        if self.column_count != len(self.columns_info.columns):
            raise ValueError("column_count does not match columns_info")
        if any(column.null_count > self.row_count for column in self.columns_info.columns):
            raise ValueError("null_count exceeds row_count")
        if self.file_type == ExperimentFileType.CSV:
            if self.columns_info.encoding is None or self.columns_info.delimiter is None:
                raise ValueError("CSV metadata requires encoding and delimiter")
            if self.columns_info.sheet_name is not None:
                raise ValueError("CSV metadata cannot contain sheet_name")
        else:
            if self.columns_info.encoding is not None or self.columns_info.delimiter is not None:
                raise ValueError("Excel metadata cannot contain CSV encoding or delimiter")
            if self.columns_info.sheet_name is None:
                raise ValueError("Excel metadata requires sheet_name")
        return self


class ExperimentFileUploadResponse(ExperimentFileMetadata):
    duplicate: bool


class ExperimentFileListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    paper_id: str
    filename: str = Field(min_length=1, max_length=255)
    file_type: ExperimentFileType
    file_size: int = Field(ge=1)
    row_count: int = Field(ge=1, le=100000)
    column_count: int = Field(ge=1, le=256)
    created_at: datetime.datetime


class ExperimentFileListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ExperimentFileListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class ExperimentFileDetail(ExperimentFileMetadata):
    pass


class NumericStats(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    mean: float
    stddev: float | None
    min: float
    max: float
    median: float


class ColumnStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    dtype: ColumnDtype
    count: int = Field(ge=0)
    null_count: int = Field(ge=0)
    stats: NumericStats | None

    @model_validator(mode="after")
    def validate_stats_for_dtype(self):
        if self.dtype in {"integer", "float"}:
            if self.count < 1 or self.stats is None:
                raise ValueError("numeric columns require statistics")
        elif self.stats is not None:
            raise ValueError("non-numeric columns cannot contain statistics")
        if self.dtype == "empty" and self.count != 0:
            raise ValueError("empty columns cannot contain values")
        return self


class SummaryStatsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    columns: list[ColumnStats] = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_summary_shape(self):
        if self.column_count != len(self.columns):
            raise ValueError("column_count does not match columns")
        if any(column.count + column.null_count != self.row_count for column in self.columns):
            raise ValueError("column counts do not match row_count")
        names = [column.name for column in self.columns]
        if len(names) != len(set(names)):
            raise ValueError("column names must be unique")
        return self


class ExperimentAnalysisTaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    paper_id: str
    task_type: Literal[TaskType.EXPERIMENT_ANALYSIS]
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    experiment_file_id: str
    created_at: datetime.datetime
    duplicate: bool


class ComparisonItem(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    metric_record_id: UUID4
    metric_task_id: UUID4
    metric_name: str = Field(min_length=1, max_length=100)
    checkpoint_type: CheckpointType
    column_name: str | None = Field(default=None, min_length=1, max_length=128)
    statistic: Literal["MEAN", "MAX"] | None
    paper_value: FiniteFloat
    experiment_value: FiniteFloat | None
    diff: FiniteFloat | None
    absolute_diff: FiniteFloat | None
    relative_diff: FiniteFloat | None
    allowed_diff: FiniteFloat | None
    status: Literal["MATCH", "MISMATCH", "UNVERIFIABLE"]
    reason: Literal[
        "AMBIGUOUS_PAPER_METRIC",
        "NO_EXPERIMENT_COLUMN",
        "AMBIGUOUS_EXPERIMENT_COLUMN",
        "UNSUPPORTED_CHECKPOINT",
        "EMPTY_NORMALIZED_NAME",
    ] | None

    @field_validator(
        "paper_value",
        "experiment_value",
        "diff",
        "absolute_diff",
        "relative_diff",
        "allowed_diff",
        mode="before",
    )
    @classmethod
    def reject_boolean_numbers(cls, value):
        if isinstance(value, bool):
            raise ValueError("boolean is not a valid number")
        return value

    @model_validator(mode="after")
    def validate_comparison_shape(self):
        optional_values = (
            self.experiment_value,
            self.diff,
            self.absolute_diff,
            self.relative_diff,
            self.allowed_diff,
        )
        if self.status == "UNVERIFIABLE":
            if self.reason is None or self.column_name is not None or self.statistic is not None:
                raise ValueError("unverifiable comparison shape is invalid")
            if any(value is not None for value in optional_values):
                raise ValueError("unverifiable comparison cannot contain computed values")
            return self
        if self.reason is not None or self.column_name is None or self.statistic is None:
            raise ValueError("comparable comparison shape is invalid")
        required_values = (self.experiment_value, self.diff, self.absolute_diff, self.allowed_diff)
        if any(value is None for value in required_values):
            raise ValueError("comparable comparison requires computed values")
        if self.checkpoint_type == CheckpointType.MEAN and self.statistic != "MEAN":
            raise ValueError("MEAN checkpoint requires MEAN statistic")
        if self.checkpoint_type == CheckpointType.MAX and self.statistic != "MAX":
            raise ValueError("MAX checkpoint requires MAX statistic")
        if self.checkpoint_type not in {CheckpointType.MEAN, CheckpointType.MAX}:
            raise ValueError("unsupported checkpoint cannot be comparable")
        if self.paper_value == 0 and self.relative_diff is not None:
            raise ValueError("zero paper value requires null relative_diff")
        if self.paper_value != 0 and self.relative_diff is None:
            raise ValueError("non-zero paper value requires relative_diff")
        if self.absolute_diff < 0 or self.allowed_diff < 0:
            raise ValueError("difference values must be non-negative")
        if self.relative_diff is not None and self.relative_diff < 0:
            raise ValueError("relative_diff must be non-negative")
        expected_diff = self.experiment_value - self.paper_value
        if not math.isclose(self.diff, expected_diff, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("diff is inconsistent")
        if not math.isclose(self.absolute_diff, abs(self.diff), rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("absolute_diff is inconsistent")
        expected_status = "MATCH" if self.absolute_diff <= self.allowed_diff else "MISMATCH"
        if self.status != expected_status:
            raise ValueError("status is inconsistent")
        return self


class PostComparisonsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_task_id: UUID4


class PostComparisonsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: UUID4
    experiment_result_id: UUID4
    metric_task_id: UUID4
    comparisons: list[ComparisonItem] = Field(min_length=1)
    duplicate: bool


class ExperimentResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    file_id: str
    task_id: str
    summary_stats: SummaryStatsResponse
    metric_comparisons: list[ComparisonItem] | None
    created_at: datetime.datetime
