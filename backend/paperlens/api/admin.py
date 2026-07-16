from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from paperlens.core.database import get_db
from paperlens.core.deps import require_admin
from paperlens.core.errors import AppError
from paperlens.models.models import User
from paperlens.schemas.admin import (
    AdminDashboardResponse,
    AdminExportListResponse,
    AdminPaperListResponse,
    AdminTaskListResponse,
    AdminUserListResponse,
    AdminUserPatchRequest,
    AdminUserPatchResponse,
    AdminUserResponse,
    AuditLogListResponse,
)
from paperlens.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


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
    role: str | None = Query(default=None, pattern="^(USER|ADMIN)$"),
    status: str | None = Query(default=None, pattern="^(ACTIVE|DISABLED)$"),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    items, total = admin_service.list_users(db, page=page, page_size=page_size, role=role, status=status, q=q)
    return AdminUserListResponse(
        items=[_user_response(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_user(
    user_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = admin_service.get_user(db, user_id)
    if data is None:
        raise AppError("NOT_FOUND", "用户不存在", 404)
    return _user_response(data)


@router.patch("/users/{user_id}", response_model=AdminUserPatchResponse)
def patch_user(
    user_id: str,
    body: AdminUserPatchRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    changed, audit_ids, target = admin_service.change_user(
        db,
        actor=admin,
        target_id=user_id,
        role=body.role,
        status=body.status,
        reason=body.reason,
    )
    if not changed:
        user_data = admin_service.get_user(db, user_id)
        return AdminUserPatchResponse(
            changed=False,
            audit_ids=[],
            user=_user_response(user_data) if user_data else _user_response({
                "id": target.id, "email": target.email, "display_name": target.display_name,
                "role": target.role, "status": target.status,
                "failed_login_count": target.failed_login_count, "locked_until": target.locked_until,
                "created_at": target.created_at, "updated_at": target.updated_at,
                "active_session_count": 0, "paper_count": 0, "task_count": 0, "export_count": 0,
            }),
        )

    db.refresh(target)
    user_data = admin_service.get_user(db, user_id)
    return AdminUserPatchResponse(
        changed=True,
        audit_ids=audit_ids,
        user=_user_response(user_data) if user_data else _user_response({
            "id": target.id, "email": target.email, "display_name": target.display_name,
            "role": target.role, "status": target.status,
            "failed_login_count": target.failed_login_count, "locked_until": target.locked_until,
            "created_at": target.created_at, "updated_at": target.updated_at,
            "active_session_count": 0, "paper_count": 0, "task_count": 0, "export_count": 0,
        }),
    )


@router.get("/papers", response_model=AdminPaperListResponse)
def list_papers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from paperlens.schemas.admin import AdminPaperItem
    items, total = admin_service.list_papers(db, page=page, page_size=page_size, status=status, user_id=user_id, q=q)
    return AdminPaperListResponse(
        items=[AdminPaperItem(**i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks", response_model=AdminTaskListResponse)
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    task_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    paper_id: str | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from paperlens.schemas.admin import AdminTaskItem
    items, total = admin_service.list_tasks(db, page=page, page_size=page_size, task_type=task_type, status=status, user_id=user_id, paper_id=paper_id)
    return AdminTaskListResponse(
        items=[AdminTaskItem(**i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/exports", response_model=AdminExportListResponse)
def list_exports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    report_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    paper_id: str | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from paperlens.schemas.admin import AdminExportItem
    items, total = admin_service.list_exports(db, page=page, page_size=page_size, report_type=report_type, status=status, user_id=user_id, paper_id=paper_id)
    return AdminExportListResponse(
        items=[AdminExportItem(**i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    actor_user_id: str | None = Query(default=None),
    action: str | None = Query(default=None, pattern="^(ADMIN_BOOTSTRAPPED|USER_ROLE_CHANGED|USER_STATUS_CHANGED)$"),
    resource_id: str | None = Query(default=None),
    created_from: datetime.datetime | None = Query(default=None),
    created_to: datetime.datetime | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from paperlens.schemas.admin import AuditLogItem, AuditLogActorInfo
    items, total = admin_service.list_audit_logs(
        db, page=page, page_size=page_size,
        actor_user_id=actor_user_id, action=action, resource_id=resource_id,
        created_from=created_from, created_to=created_to,
    )
    return AuditLogListResponse(
        items=[AuditLogItem(
            id=i["id"],
            actor=AuditLogActorInfo(**i["actor"]),
            action=i["action"],
            resource_type=i["resource_type"],
            resource_id=i["resource_id"],
            reason=i["reason"],
            before_state=i["before_state"],
            after_state=i["after_state"],
            created_at=i["created_at"],
        ) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )