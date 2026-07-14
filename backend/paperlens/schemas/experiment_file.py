from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from paperlens.core.enums import ExperimentFileType


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
