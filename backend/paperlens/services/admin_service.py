from __future__ import annotations

import datetime
import logging
import re
import uuid

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from paperlens.core.enums import UserRole, UserStatus
from paperlens.core.errors import AppError
from paperlens.models.models import AdminAuditLog, AuthSession, PasswordResetToken, User

logger = logging.getLogger(__name__)

_ALLOWED_STATE_KEYS = {"role", "status"}


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _validate_state_keys(state: dict) -> None:
    for key in state:
        if key not in _ALLOWED_STATE_KEYS:
            raise AppError("VALIDATION_ERROR", f"before/after_state 不允许键: {key}", 422)


def _build_state(*, role: str | None = None, status: str | None = None) -> dict:
    state: dict = {}
    if role is not None:
        state["role"] = role
    if status is not None:
        state["status"] = status
    return state


def _insert_audit(
    db: Session,
    *,
    actor_user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    reason: str,
    before_state: dict,
    after_state: dict,
) -> str:
    _validate_state_keys(before_state)
    _validate_state_keys(after_state)
    audit_id = str(uuid.uuid4())
    log = AdminAuditLog(
        id=audit_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        reason=reason,
        before_state=before_state,
        after_state=after_state,
    )
    db.add(log)
    db.flush()
    return audit_id


def admin_bootstrap(db: Session, *, user_id: str, reason: str) -> str:
    if len(reason) < 8 or len(reason) > 500:
        raise AppError("VALIDATION_ERROR", "reason 长度须在 8~500 之间", 422)
    if re.search(r"[\x00-\x1f]", reason):
        raise AppError("VALIDATION_ERROR", "reason 不能包含控制字符", 422)

    active_admins = (
        db.query(User)
        .filter(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE)
        .with_for_update()
        .all()
    )
    if len(active_admins) > 0:
        raise AppError("CONFLICT", "已存在活跃管理员，无法再次引导", 409)

    target = db.query(User).filter(User.id == user_id).with_for_update().first()
    if target is None:
        raise AppError("NOT_FOUND", "目标用户不存在", 404)
    if target.status != UserStatus.ACTIVE:
        raise AppError("VALIDATION_ERROR", "目标用户不是活跃状态", 422)
    if target.role == UserRole.ADMIN:
        raise AppError("CONFLICT", "目标用户已是管理员", 409)

    before = _build_state(role=target.role, status=target.status)
    target.role = UserRole.ADMIN
    after = _build_state(role=target.role, status=target.status)
    db.flush()

    audit_id = _insert_audit(
        db,
        actor_user_id=user_id,
        action="ADMIN_BOOTSTRAPPED",
        resource_type="USER",
        resource_id=user_id,
        reason=reason,
        before_state=before,
        after_state=after,
    )

    now = _utcnow()
    sessions = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .all()
    )
    for session in sessions:
        session.revoked_at = now
        session.revoke_reason = "admin_bootstrap"
    db.flush()

    db.commit()
    logger.info("stage=admin_bootstrap actor=%s target=%s audit=%s", user_id, user_id, audit_id)
    return audit_id


def change_user(
    db: Session,
    *,
    actor: User,
    target_id: str,
    role: str | None = None,
    status: str | None = None,
    reason: str,
) -> tuple[bool, list[str], User]:
    if role is None and status is None:
        raise AppError("VALIDATION_ERROR", "role 和 status 至少需要提供一个", 422)
    if len(reason) < 8 or len(reason) > 500:
        raise AppError("VALIDATION_ERROR", "reason 长度须在 8~500 之间", 422)
    if re.search(r"[\x00-\x1f]", reason):
        raise AppError("VALIDATION_ERROR", "reason 不能包含控制字符", 422)
    if role is not None and role not in (UserRole.USER, UserRole.ADMIN):
        raise AppError("VALIDATION_ERROR", "role 只允许 USER 或 ADMIN", 422)
    if status is not None and status not in (UserStatus.ACTIVE, UserStatus.DISABLED):
        raise AppError("VALIDATION_ERROR", "status 只允许 ACTIVE 或 DISABLED", 422)

    active_admins = (
        db.query(User)
        .filter(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE)
        .with_for_update()
        .all()
    )

    target = db.query(User).filter(User.id == target_id).with_for_update().first()
    if target is None:
        raise AppError("NOT_FOUND", "目标用户不存在", 404)

    if actor.id == target_id:
        if role is not None and role != UserRole.ADMIN:
            raise AppError("CONFLICT", "管理员不能自我降级", 409)
        if status is not None and status != UserStatus.ACTIVE:
            raise AppError("CONFLICT", "管理员不能自我禁用", 409)

    audit_ids: list[str] = []
    changed = False

    if role is not None and target.role != role:
        before = _build_state(role=target.role)
        target.role = role
        after = _build_state(role=target.role)
        db.flush()
        aid = _insert_audit(
            db,
            actor_user_id=actor.id,
            action="USER_ROLE_CHANGED",
            resource_type="USER",
            resource_id=target_id,
            reason=reason,
            before_state=before,
            after_state=after,
        )
        audit_ids.append(aid)
        changed = True

    if status is not None and target.status != status:
        before = _build_state(status=target.status)
        target.status = status
        after = _build_state(status=target.status)
        db.flush()
        aid = _insert_audit(
            db,
            actor_user_id=actor.id,
            action="USER_STATUS_CHANGED",
            resource_type="USER",
            resource_id=target_id,
            reason=reason,
            before_state=before,
            after_state=after,
        )
        audit_ids.append(aid)
        changed = True

    if not changed:
        db.flush()
        return False, [], target

    remaining_admins = sum(
        1 for u in active_admins if u.id != target_id and u.status == UserStatus.ACTIVE
    )
    if target.role == UserRole.ADMIN and target.status == UserStatus.ACTIVE:
        remaining_admins += 1
    if remaining_admins < 1:
        db.rollback()
        raise AppError("CONFLICT", "操作将导致无活跃管理员", 409)

    now = _utcnow()
    sessions = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == target_id, AuthSession.revoked_at.is_(None))
        .all()
    )
    for session in sessions:
        session.revoked_at = now
        session.revoke_reason = "admin_user_change"
    db.flush()

    if status == UserStatus.DISABLED:
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == target_id,
            PasswordResetToken.used_at.is_(None),
        ).update({"used_at": now}, synchronize_session=False)
        db.flush()

    db.commit()
    logger.info(
        "stage=admin_user_change actor=%s target=%s changed=%s audits=%s",
        actor.id, target_id, changed, ",".join(audit_ids),
    )
    return changed, audit_ids, target


def get_dashboard(db: Session) -> dict:
    users_by_role: dict[str, int] = {}
    for row in db.query(User.role, func.count(User.id)).group_by(User.role).all():
        users_by_role[row[0]] = row[1]

    users_by_status: dict[str, int] = {}
    for row in db.query(User.status, func.count(User.id)).group_by(User.status).all():
        users_by_status[row[0]] = row[1]

    papers_by_status: dict[str, int] = {}
    for row in db.query(User.__table__.columns if False else None, func.count(None) if False else None):
        break
    from paperlens.models.models import Paper
    for row in db.query(Paper.status, func.count(Paper.id)).group_by(Paper.status).all():
        papers_by_status[row[0]] = row[1]

    from paperlens.models.models import AnalysisTask
    tasks_by_type: dict[str, int] = {}
    for row in db.query(AnalysisTask.task_type, func.count(AnalysisTask.id)).group_by(AnalysisTask.task_type).all():
        tasks_by_type[row[0]] = row[1]

    tasks_by_status: dict[str, int] = {}
    for row in db.query(AnalysisTask.status, func.count(AnalysisTask.id)).group_by(AnalysisTask.status).all():
        tasks_by_status[row[0]] = row[1]

    from paperlens.models.models import ExportReport
    exports_by_type: dict[str, int] = {}
    for row in db.query(ExportReport.report_type, func.count(ExportReport.id)).group_by(ExportReport.report_type).all():
        exports_by_type[row[0]] = row[1]

    exports_by_status: dict[str, int] = {}
    for row in db.query(ExportReport.status, func.count(ExportReport.id)).group_by(ExportReport.status).all():
        exports_by_status[row[0]] = row[1]

    return {
        "users_by_role": users_by_role,
        "users_by_status": users_by_status,
        "papers_by_status": papers_by_status,
        "tasks_by_type": tasks_by_type,
        "tasks_by_status": tasks_by_status,
        "exports_by_type": exports_by_type,
        "exports_by_status": exports_by_status,
    }


def list_users(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    role: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> tuple[list[dict], int]:
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    if q and len(q) >= 1 and len(q) <= 100:
        normalized = q.strip().casefold()
        query = query.filter(
            (func.lower(User.email).contains(normalized))
            | (func.lower(User.display_name).contains(normalized))
        )

    total = query.count()
    rows = (
        query.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for u in rows:
        active_session_count = (
            db.query(AuthSession)
            .filter(AuthSession.user_id == u.id, AuthSession.revoked_at.is_(None))
            .count()
        )
        from paperlens.models.models import Paper, AnalysisTask, ExportReport
        paper_count = db.query(Paper).filter(Paper.user_id == u.id).count()
        task_count = db.query(AnalysisTask).filter(AnalysisTask.user_id == u.id).count()
        export_count = db.query(ExportReport).filter(ExportReport.user_id == u.id).count()
        items.append({
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role,
            "status": u.status,
            "failed_login_count": u.failed_login_count,
            "locked_until": u.locked_until,
            "created_at": u.created_at,
            "updated_at": u.updated_at,
            "active_session_count": active_session_count,
            "paper_count": paper_count,
            "task_count": task_count,
            "export_count": export_count,
        })
    return items, total


def get_user(db: Session, user_id: str) -> dict | None:
    u = db.query(User).filter(User.id == user_id).first()
    if u is None:
        return None
    active_session_count = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == u.id, AuthSession.revoked_at.is_(None))
        .count()
    )
    from paperlens.models.models import Paper, AnalysisTask, ExportReport
    paper_count = db.query(Paper).filter(Paper.user_id == u.id).count()
    task_count = db.query(AnalysisTask).filter(AnalysisTask.user_id == u.id).count()
    export_count = db.query(ExportReport).filter(ExportReport.user_id == u.id).count()
    return {
        "id": u.id,
        "email": u.email,
        "display_name": u.display_name,
        "role": u.role,
        "status": u.status,
        "failed_login_count": u.failed_login_count,
        "locked_until": u.locked_until,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
        "active_session_count": active_session_count,
        "paper_count": paper_count,
        "task_count": task_count,
        "export_count": export_count,
    }


def list_papers(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    user_id: str | None = None,
    q: str | None = None,
) -> tuple[list[dict], int]:
    from paperlens.models.models import Paper
    query = db.query(Paper)
    if status:
        query = query.filter(Paper.status == status)
    if user_id:
        query = query.filter(Paper.user_id == user_id)
    if q and len(q) >= 1 and len(q) <= 100:
        normalized = q.strip().casefold()
        query = query.filter(func.lower(Paper.title).contains(normalized))

    total = query.count()
    rows = (
        query.order_by(Paper.created_at.desc(), Paper.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for p in rows:
        owner = db.query(User).filter(User.id == p.user_id).first()
        items.append({
            "id": p.id,
            "user_id": p.user_id,
            "owner_email": owner.email if owner else "",
            "title": p.title,
            "filename": p.filename,
            "file_size": p.file_size,
            "page_count": p.page_count,
            "status": p.status,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        })
    return items, total


def list_tasks(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    task_type: str | None = None,
    status: str | None = None,
    user_id: str | None = None,
    paper_id: str | None = None,
) -> tuple[list[dict], int]:
    from paperlens.models.models import AnalysisTask
    query = db.query(AnalysisTask)
    if task_type:
        query = query.filter(AnalysisTask.task_type == task_type)
    if status:
        query = query.filter(AnalysisTask.status == status)
    if user_id:
        query = query.filter(AnalysisTask.user_id == user_id)
    if paper_id:
        query = query.filter(AnalysisTask.paper_id == paper_id)

    total = query.count()
    rows = (
        query.order_by(AnalysisTask.created_at.desc(), AnalysisTask.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for t in rows:
        items.append({
            "id": t.id,
            "paper_id": t.paper_id,
            "user_id": t.user_id,
            "task_type": t.task_type,
            "status": t.status,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        })
    return items, total


def list_exports(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    report_type: str | None = None,
    status: str | None = None,
    user_id: str | None = None,
    paper_id: str | None = None,
) -> tuple[list[dict], int]:
    from paperlens.models.models import ExportReport
    query = db.query(ExportReport)
    if report_type:
        query = query.filter(ExportReport.report_type == report_type)
    if status:
        query = query.filter(ExportReport.status == status)
    if user_id:
        query = query.filter(ExportReport.user_id == user_id)
    if paper_id:
        query = query.filter(ExportReport.paper_id == paper_id)

    total = query.count()
    rows = (
        query.order_by(ExportReport.created_at.desc(), ExportReport.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for e in rows:
        items.append({
            "id": e.id,
            "paper_id": e.paper_id,
            "user_id": e.user_id,
            "report_type": e.report_type,
            "status": e.status,
            "created_at": e.created_at,
            "completed_at": e.completed_at,
        })
    return items, total


def list_audit_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    actor_user_id: str | None = None,
    action: str | None = None,
    resource_id: str | None = None,
    created_from: datetime.datetime | None = None,
    created_to: datetime.datetime | None = None,
) -> tuple[list[dict], int]:
    if created_from and created_to and created_from > created_to:
        raise AppError("VALIDATION_ERROR", "created_from 不能晚于 created_to", 422)

    query = db.query(AdminAuditLog)
    if actor_user_id:
        query = query.filter(AdminAuditLog.actor_user_id == actor_user_id)
    if action:
        query = query.filter(AdminAuditLog.action == action)
    if resource_id:
        query = query.filter(AdminAuditLog.resource_id == resource_id)
    if created_from:
        query = query.filter(AdminAuditLog.created_at >= created_from)
    if created_to:
        query = query.filter(AdminAuditLog.created_at <= created_to)

    total = query.count()
    rows = (
        query.order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for log in rows:
        actor = db.query(User).filter(User.id == log.actor_user_id).first()
        items.append({
            "id": log.id,
            "actor": {
                "id": log.actor_user_id,
                "email": actor.email if actor else "",
            },
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "reason": log.reason,
            "before_state": log.before_state,
            "after_state": log.after_state,
            "created_at": log.created_at,
        })
    return items, total