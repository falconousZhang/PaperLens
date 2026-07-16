from __future__ import annotations

import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminUserPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str | None = Field(default=None, pattern="^(USER|ADMIN)$")
    status: str | None = Field(default=None, pattern="^(ACTIVE|DISABLED)$")
    reason: str = Field(min_length=8, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_no_control_chars(cls, v: str) -> str:
        if re.search(r"[\x00-\x1f]", v):
            raise ValueError("reason must not contain control characters")
        return v

    @field_validator("role", "status")
    @classmethod
    def at_least_one_change(cls, v: str | None, info) -> str | None:
        return v


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
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


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