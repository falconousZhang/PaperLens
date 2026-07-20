from __future__ import annotations

import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AdminUserPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["USER", "ADMIN"] | None = None
    status: Literal["ACTIVE", "DISABLED"] | None = None
    reason: str = Field(min_length=8, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        normalized = v.strip()
        if re.search(r"[\x00-\x1f\x7f]", normalized):
            raise ValueError("reason must not contain control characters")
        return normalized

    @model_validator(mode="after")
    def require_change(self):
        if self.role is None and self.status is None:
            raise ValueError("role or status is required")
        return self


class AdminDashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    users_by_role: dict[str, int]
    users_by_status: dict[str, int]
    papers_by_status: dict[str, int]
    tasks_by_type: dict[str, int]
    tasks_by_status: dict[str, int]
    exports_by_type: dict[str, int]
    exports_by_status: dict[str, int]


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    display_name: str
    role: str
    status: str
    failed_login_count: int
    locked_until: datetime.datetime | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    active_session_count: int
    paper_count: int
    task_count: int
    export_count: int


class AdminUserListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class AdminUserPatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changed: bool
    audit_ids: list[str]
    user: AdminUserResponse


class AdminPaperItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    owner_email: str
    title: str
    filename: str
    file_size: int
    page_count: int | None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AdminPaperListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminPaperItem]
    total: int
    page: int
    page_size: int


class AdminTaskItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    paper_id: str
    user_id: str
    task_type: str
    status: str
    progress: int
    error_message: str | None
    started_at: datetime.datetime | None
    completed_at: datetime.datetime | None
    created_at: datetime.datetime


class AdminTaskListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminTaskItem]
    total: int
    page: int
    page_size: int


class AdminExportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    paper_id: str
    user_id: str
    report_type: str
    status: str
    file_size: int | None
    error_message: str | None
    created_at: datetime.datetime
    completed_at: datetime.datetime | None


class AdminExportListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminExportItem]
    total: int
    page: int
    page_size: int


class AuditLogActorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str


class AuditLogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    actor: AuditLogActorInfo
    action: str
    resource_type: str
    resource_id: str
    reason: str
    before_state: dict
    after_state: dict
    created_at: datetime.datetime


class AuditLogListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int
