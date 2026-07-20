from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime, StringConstraints, UUID4
from sqlalchemy.orm import Session

from paperlens.core.database import get_db
from paperlens.core.deps import require_admin
from paperlens.core.enums import ExportStatus, PaperStatus, TaskStatus, TaskType, UserRole, UserStatus
from paperlens.core.errors import AppError
from paperlens.models.models import User
from paperlens.schemas.admin import (
    AdminDashboardResponse,
    AdminExportItem,
    AdminExportListResponse,
    AdminPaperItem,
    AdminPaperListResponse,
    AdminTaskItem,
    AdminTaskListResponse,
    AdminUserListResponse,
    AdminUserPatchRequest,
    AdminUserPatchResponse,
    AdminUserResponse,
    AuditLogActorInfo,
    AuditLogItem,
    AuditLogListResponse,
)
from paperlens.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])

SearchText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[^\x00-\x1f\x7f]+$",
    ),
]
ReportType = Literal["MARKDOWN", "PDF", "DOCX"]
AuditAction = Literal["ADMIN_BOOTSTRAPPED", "USER_ROLE_CHANGED", "USER_STATUS_CHANGED"]


def _user_response(data: dict) -> AdminUserResponse:
    return AdminUserResponse(**data)


@router.get("/dashboard", response_model=AdminDashboardResponse)
def get_dashboard(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return AdminDashboardResponse(**admin_service.get_dashboard(db))


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: UserRole | None = Query(default=None),
    status: UserStatus | None = Query(default=None),
    q: SearchText | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    items, total = admin_service.list_users(
        db,
        page=page,
        page_size=page_size,
        role=role,
        status=status,
        q=q,
    )
    return AdminUserListResponse(
        items=[_user_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_user(
    user_id: UUID4,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = admin_service.get_user(db, str(user_id))
    if data is None:
        raise AppError("NOT_FOUND", "用户不存在", 404)
    return _user_response(data)


@router.patch("/users/{user_id}", response_model=AdminUserPatchResponse)
def patch_user(
    user_id: UUID4,
    body: AdminUserPatchRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target_id = str(user_id)
    changed, audit_ids, _target = admin_service.change_user(
        db,
        actor=admin,
        target_id=target_id,
        role=body.role,
        status=body.status,
        reason=body.reason,
    )
    user_data = admin_service.get_user(db, target_id)
    if user_data is None:
        raise AppError("ADMIN_WRITE_FAILED", "管理员操作结果无法读取，请刷新后重试", 500)
    return AdminUserPatchResponse(
        changed=changed,
        audit_ids=audit_ids,
        user=_user_response(user_data),
    )


@router.get("/papers", response_model=AdminPaperListResponse)
def list_papers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: PaperStatus | None = Query(default=None),
    user_id: UUID4 | None = Query(default=None),
    q: SearchText | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    items, total = admin_service.list_papers(
        db,
        page=page,
        page_size=page_size,
        status=status,
        user_id=str(user_id) if user_id else None,
        q=q,
    )
    return AdminPaperListResponse(
        items=[AdminPaperItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks", response_model=AdminTaskListResponse)
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    task_type: TaskType | None = Query(default=None),
    status: TaskStatus | None = Query(default=None),
    user_id: UUID4 | None = Query(default=None),
    paper_id: UUID4 | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    items, total = admin_service.list_tasks(
        db,
        page=page,
        page_size=page_size,
        task_type=task_type,
        status=status,
        user_id=str(user_id) if user_id else None,
        paper_id=str(paper_id) if paper_id else None,
    )
    return AdminTaskListResponse(
        items=[AdminTaskItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/exports", response_model=AdminExportListResponse)
def list_exports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    report_type: ReportType | None = Query(default=None),
    status: ExportStatus | None = Query(default=None),
    user_id: UUID4 | None = Query(default=None),
    paper_id: UUID4 | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    items, total = admin_service.list_exports(
        db,
        page=page,
        page_size=page_size,
        report_type=report_type,
        status=status,
        user_id=str(user_id) if user_id else None,
        paper_id=str(paper_id) if paper_id else None,
    )
    return AdminExportListResponse(
        items=[AdminExportItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    actor_user_id: UUID4 | None = Query(default=None),
    action: AuditAction | None = Query(default=None),
    resource_id: UUID4 | None = Query(default=None),
    created_from: AwareDatetime | None = Query(default=None),
    created_to: AwareDatetime | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    items, total = admin_service.list_audit_logs(
        db,
        page=page,
        page_size=page_size,
        actor_user_id=str(actor_user_id) if actor_user_id else None,
        action=action,
        resource_id=str(resource_id) if resource_id else None,
        created_from=created_from,
        created_to=created_to,
    )
    return AuditLogListResponse(
        items=[
            AuditLogItem(
                id=item["id"],
                actor=AuditLogActorInfo(**item["actor"]),
                action=item["action"],
                resource_type=item["resource_type"],
                resource_id=item["resource_id"],
                reason=item["reason"],
                before_state=item["before_state"],
                after_state=item["after_state"],
                created_at=item["created_at"],
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
