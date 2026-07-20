from __future__ import annotations

import datetime
import logging
import re
import uuid

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from paperlens.core.enums import UserRole, UserStatus
from paperlens.core.errors import AppError
from paperlens.models.models import (
    AdminAuditLog,
    AnalysisTask,
    AuthSession,
    ExportReport,
    Paper,
    PasswordResetToken,
    User,
)

logger = logging.getLogger(__name__)

_ADMIN_LOCK_KEY = 0x50415045524C454E
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_ACTIONS = {
    "ADMIN_BOOTSTRAPPED",
    "USER_ROLE_CHANGED",
    "USER_STATUS_CHANGED",
}


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _normalize_reason(reason: str) -> str:
    normalized = reason.strip()
    if not 8 <= len(normalized) <= 500:
        raise AppError("VALIDATION_ERROR", "操作原因长度必须在 8 到 500 个字符之间", 422)
    if _CONTROL_CHARS.search(normalized):
        raise AppError("VALIDATION_ERROR", "操作原因不能包含控制字符", 422)
    return normalized


def _validate_audit_state(action: str, before_state: dict, after_state: dict) -> None:
    if action not in _ACTIONS:
        raise AppError("VALIDATION_ERROR", "不支持的审计动作", 422)
    if action == "ADMIN_BOOTSTRAPPED":
        valid = before_state == {"role": "USER", "status": "ACTIVE"} and after_state == {
            "role": "ADMIN",
            "status": "ACTIVE",
        }
    elif action == "USER_ROLE_CHANGED":
        valid = (
            set(before_state) == {"role"}
            and set(after_state) == {"role"}
            and before_state["role"] in {"USER", "ADMIN"}
            and after_state["role"] in {"USER", "ADMIN"}
            and before_state != after_state
        )
    else:
        valid = (
            set(before_state) == {"status"}
            and set(after_state) == {"status"}
            and before_state["status"] in {"ACTIVE", "DISABLED"}
            and after_state["status"] in {"ACTIVE", "DISABLED"}
            and before_state != after_state
        )
    if not valid:
        raise AppError("VALIDATION_ERROR", "审计状态与动作不匹配", 422)


def _insert_audit(
    db: Session,
    *,
    audit_id: str,
    actor_user_id: str,
    action: str,
    resource_id: str,
    reason: str,
    before_state: dict,
    after_state: dict,
) -> None:
    _validate_audit_state(action, before_state, after_state)
    db.add(
        AdminAuditLog(
            id=audit_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type="USER",
            resource_id=resource_id,
            reason=reason,
            before_state=before_state,
            after_state=after_state,
        )
    )
    db.flush()


def _rollback(db: Session) -> None:
    try:
        db.rollback()
    except Exception:
        logger.exception("stage=admin_rollback_failed error_type=database")


def _lock_admin_namespace(db: Session) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _ADMIN_LOCK_KEY})


def _commit_with_recovery(
    db: Session,
    *,
    stage: str,
    target_id: str,
    expected_role: str,
    expected_status: str,
    audit_ids: list[str],
) -> User:
    try:
        db.commit()
        target = db.query(User).filter(User.id == target_id).one()
        return target
    except Exception as exc:
        error_type = type(exc).__name__
        _rollback(db)
        try:
            target = db.query(User).filter(User.id == target_id).one_or_none()
            audit_count = (
                db.query(func.count(AdminAuditLog.id))
                .filter(AdminAuditLog.id.in_(audit_ids))
                .scalar()
            )
            recovered = (
                target is not None
                and target.role == expected_role
                and target.status == expected_status
                and audit_count == len(audit_ids)
            )
        except Exception as recovery_exc:
            _rollback(db)
            logger.error(
                "stage=%s_commit_recovery_failed target=%s error_type=%s",
                stage,
                target_id,
                type(recovery_exc).__name__,
            )
            raise AppError("ADMIN_WRITE_FAILED", "管理员操作未能确认，请刷新后重试", 500) from recovery_exc
        if recovered:
            logger.warning(
                "stage=%s_commit_recovered target=%s error_type=%s",
                stage,
                target_id,
                error_type,
            )
            return target
        _rollback(db)
        logger.error(
            "stage=%s_commit_failed target=%s error_type=%s",
            stage,
            target_id,
            error_type,
        )
        raise AppError("ADMIN_WRITE_FAILED", "管理员操作失败，请稍后重试", 500) from exc


def admin_bootstrap(db: Session, *, user_id: str, reason: str) -> str:
    normalized_reason = _normalize_reason(reason)
    audit_id = str(uuid.uuid4())
    try:
        _lock_admin_namespace(db)
        active_admins = (
            db.query(User)
            .filter(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE)
            .order_by(User.id)
            .with_for_update()
            .all()
        )
        if active_admins:
            raise AppError("CONFLICT", "已存在活动管理员，不能再次执行首次引导", 409)

        target = (
            db.query(User)
            .filter(User.id == user_id)
            .with_for_update()
            .populate_existing()
            .one_or_none()
        )
        if target is None:
            raise AppError("NOT_FOUND", "目标用户不存在", 404)
        if target.status != UserStatus.ACTIVE:
            raise AppError("VALIDATION_ERROR", "目标用户必须处于活动状态", 422)
        if target.role != UserRole.USER:
            raise AppError("CONFLICT", "目标用户不是可引导的普通用户", 409)

        target.role = UserRole.ADMIN
        _insert_audit(
            db,
            audit_id=audit_id,
            actor_user_id=user_id,
            action="ADMIN_BOOTSTRAPPED",
            resource_id=user_id,
            reason=normalized_reason,
            before_state={"role": "USER", "status": "ACTIVE"},
            after_state={"role": "ADMIN", "status": "ACTIVE"},
        )

        now = _utcnow()
        db.query(AuthSession).filter(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        ).update(
            {"revoked_at": now, "revoke_reason": "admin_bootstrap"},
            synchronize_session=False,
        )
        _commit_with_recovery(
            db,
            stage="admin_bootstrap",
            target_id=user_id,
            expected_role=UserRole.ADMIN,
            expected_status=UserStatus.ACTIVE,
            audit_ids=[audit_id],
        )
    except AppError:
        _rollback(db)
        raise
    except Exception as exc:
        _rollback(db)
        logger.error(
            "stage=admin_bootstrap_failed target=%s error_type=%s",
            user_id,
            type(exc).__name__,
        )
        raise AppError("ADMIN_BOOTSTRAP_FAILED", "管理员引导失败，请稍后重试", 500) from exc

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
        raise AppError("VALIDATION_ERROR", "role 和 status 至少提供一个", 422)
    normalized_reason = _normalize_reason(reason)
    if role is not None and role not in {UserRole.USER, UserRole.ADMIN}:
        raise AppError("VALIDATION_ERROR", "role 只允许 USER 或 ADMIN", 422)
    if status is not None and status not in {UserStatus.ACTIVE, UserStatus.DISABLED}:
        raise AppError("VALIDATION_ERROR", "status 只允许 ACTIVE 或 DISABLED", 422)

    actor_was_active_admin = actor.role == UserRole.ADMIN and actor.status == UserStatus.ACTIVE
    try:
        _lock_admin_namespace(db)
        active_admins = (
            db.query(User)
            .filter(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE)
            .order_by(User.id)
            .with_for_update()
            .populate_existing()
            .all()
        )
        locked_users = (
            db.query(User)
            .filter(User.id.in_(sorted({actor.id, target_id})))
            .order_by(User.id)
            .with_for_update()
            .populate_existing()
            .all()
        )
        users_by_id = {item.id: item for item in locked_users}
        locked_actor = users_by_id.get(actor.id)
        target = users_by_id.get(target_id)
        if (
            locked_actor is None
            or locked_actor.role != UserRole.ADMIN
            or locked_actor.status != UserStatus.ACTIVE
        ):
            if actor_was_active_admin:
                raise AppError("CONFLICT", "管理员权限已被并发操作改变，请刷新后重试", 409)
            raise AppError("FORBIDDEN", "当前账户已无管理员权限", 403)
        if target is None:
            raise AppError("NOT_FOUND", "目标用户不存在", 404)

        if actor.id == target_id:
            if role is not None and role != UserRole.ADMIN:
                raise AppError("CONFLICT", "管理员不能自我降级", 409)
            if status is not None and status != UserStatus.ACTIVE:
                raise AppError("CONFLICT", "管理员不能自我禁用", 409)

        audit_ids: list[str] = []
        if role is not None and target.role != role:
            before_role = str(target.role)
            target.role = role
            audit_id = str(uuid.uuid4())
            _insert_audit(
                db,
                audit_id=audit_id,
                actor_user_id=locked_actor.id,
                action="USER_ROLE_CHANGED",
                resource_id=target_id,
                reason=normalized_reason,
                before_state={"role": before_role},
                after_state={"role": str(target.role)},
            )
            audit_ids.append(audit_id)

        if status is not None and target.status != status:
            before_status = str(target.status)
            target.status = status
            audit_id = str(uuid.uuid4())
            _insert_audit(
                db,
                audit_id=audit_id,
                actor_user_id=locked_actor.id,
                action="USER_STATUS_CHANGED",
                resource_id=target_id,
                reason=normalized_reason,
                before_state={"status": before_status},
                after_state={"status": str(target.status)},
            )
            audit_ids.append(audit_id)

        if not audit_ids:
            return False, [], target

        db.flush()
        remaining_admins = (
            db.query(func.count(User.id))
            .filter(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE)
            .scalar()
        )
        if remaining_admins < 1:
            raise AppError("CONFLICT", "操作后必须至少保留一个活动管理员", 409)

        now = _utcnow()
        db.query(AuthSession).filter(
            AuthSession.user_id == target_id,
            AuthSession.revoked_at.is_(None),
        ).update(
            {"revoked_at": now, "revoke_reason": "admin_user_change"},
            synchronize_session=False,
        )
        if target.status == UserStatus.DISABLED:
            db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == target_id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            ).update({"used_at": now}, synchronize_session=False)

        target = _commit_with_recovery(
            db,
            stage="admin_user_change",
            target_id=target_id,
            expected_role=str(target.role),
            expected_status=str(target.status),
            audit_ids=audit_ids,
        )
    except AppError:
        _rollback(db)
        raise
    except Exception as exc:
        _rollback(db)
        logger.error(
            "stage=admin_user_change_failed actor=%s target=%s error_type=%s",
            actor.id,
            target_id,
            type(exc).__name__,
        )
        raise AppError("ADMIN_WRITE_FAILED", "管理员操作失败，请稍后重试", 500) from exc

    logger.info(
        "stage=admin_user_change actor=%s target=%s audits=%s",
        actor.id,
        target_id,
        ",".join(audit_ids),
    )
    return True, audit_ids, target


def get_dashboard(db: Session) -> dict:
    def grouped(model, group_column, id_column) -> dict[str, int]:
        return {
            str(value): count
            for value, count in db.query(group_column, func.count(id_column)).group_by(group_column).all()
        }

    return {
        "users_by_role": grouped(User, User.role, User.id),
        "users_by_status": grouped(User, User.status, User.id),
        "papers_by_status": grouped(Paper, Paper.status, Paper.id),
        "tasks_by_type": grouped(AnalysisTask, AnalysisTask.task_type, AnalysisTask.id),
        "tasks_by_status": grouped(AnalysisTask, AnalysisTask.status, AnalysisTask.id),
        "exports_by_type": grouped(ExportReport, ExportReport.report_type, ExportReport.id),
        "exports_by_status": grouped(ExportReport, ExportReport.status, ExportReport.id),
    }


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _user_query(db: Session, now: datetime.datetime):
    active_sessions = (
        select(func.count(AuthSession.sid))
        .where(
            AuthSession.user_id == User.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .correlate(User)
        .scalar_subquery()
    )
    paper_count = select(func.count(Paper.id)).where(Paper.user_id == User.id).correlate(User).scalar_subquery()
    task_count = (
        select(func.count(AnalysisTask.id)).where(AnalysisTask.user_id == User.id).correlate(User).scalar_subquery()
    )
    export_count = (
        select(func.count(ExportReport.id)).where(ExportReport.user_id == User.id).correlate(User).scalar_subquery()
    )
    return db.query(
        User.id,
        User.email,
        User.display_name,
        User.role,
        User.status,
        User.failed_login_count,
        User.locked_until,
        User.created_at,
        User.updated_at,
        active_sessions.label("active_session_count"),
        paper_count.label("paper_count"),
        task_count.label("task_count"),
        export_count.label("export_count"),
    )


def _user_row(row) -> dict:
    return {
        "id": row.id,
        "email": row.email,
        "display_name": row.display_name,
        "role": row.role,
        "status": row.status,
        "failed_login_count": row.failed_login_count,
        "locked_until": row.locked_until,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "active_session_count": row.active_session_count,
        "paper_count": row.paper_count,
        "task_count": row.task_count,
        "export_count": row.export_count,
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
    query = _user_query(db, _utcnow())
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    if q:
        pattern = f"%{_escape_like(q.strip().casefold())}%"
        query = query.filter(
            func.lower(User.email).like(pattern, escape="\\")
            | func.lower(User.display_name).like(pattern, escape="\\")
        )
    total = query.order_by(None).count()
    rows = (
        query.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [_user_row(row) for row in rows], total


def get_user(db: Session, user_id: str) -> dict | None:
    row = _user_query(db, _utcnow()).filter(User.id == user_id).one_or_none()
    return _user_row(row) if row is not None else None


def list_papers(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    user_id: str | None = None,
    q: str | None = None,
) -> tuple[list[dict], int]:
    query = db.query(
        Paper.id,
        Paper.user_id,
        User.email.label("owner_email"),
        Paper.title,
        Paper.filename,
        Paper.file_size,
        Paper.page_count,
        Paper.status,
        Paper.created_at,
        Paper.updated_at,
    ).join(User, User.id == Paper.user_id)
    if status:
        query = query.filter(Paper.status == status)
    if user_id:
        query = query.filter(Paper.user_id == user_id)
    if q:
        pattern = f"%{_escape_like(q.strip().casefold())}%"
        query = query.filter(
            func.lower(Paper.title).like(pattern, escape="\\")
            | func.lower(Paper.filename).like(pattern, escape="\\")
        )
    total = query.order_by(None).count()
    rows = (
        query.order_by(Paper.created_at.desc(), Paper.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [dict(row._mapping) for row in rows], total


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
    query = db.query(
        AnalysisTask.id,
        AnalysisTask.paper_id,
        AnalysisTask.user_id,
        AnalysisTask.task_type,
        AnalysisTask.status,
        AnalysisTask.progress,
        AnalysisTask.started_at,
        AnalysisTask.completed_at,
        AnalysisTask.created_at,
    )
    if task_type:
        query = query.filter(AnalysisTask.task_type == task_type)
    if status:
        query = query.filter(AnalysisTask.status == status)
    if user_id:
        query = query.filter(AnalysisTask.user_id == user_id)
    if paper_id:
        query = query.filter(AnalysisTask.paper_id == paper_id)
    total = query.order_by(None).count()
    rows = (
        query.order_by(AnalysisTask.created_at.desc(), AnalysisTask.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [
        {
            **dict(row._mapping),
            "error_message": "任务执行失败" if row.status == "FAILED" else None,
        }
        for row in rows
    ], total


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
    query = db.query(
        ExportReport.id,
        ExportReport.paper_id,
        ExportReport.user_id,
        ExportReport.report_type,
        ExportReport.status,
        ExportReport.file_size,
        ExportReport.created_at,
        ExportReport.completed_at,
    )
    if report_type:
        query = query.filter(ExportReport.report_type == report_type)
    if status:
        query = query.filter(ExportReport.status == status)
    if user_id:
        query = query.filter(ExportReport.user_id == user_id)
    if paper_id:
        query = query.filter(ExportReport.paper_id == paper_id)
    total = query.order_by(None).count()
    rows = (
        query.order_by(ExportReport.created_at.desc(), ExportReport.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [
        {
            **dict(row._mapping),
            "error_message": "报告生成失败" if row.status == "FAILED" else None,
        }
        for row in rows
    ], total


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
    for value in (created_from, created_to):
        if value is not None and value.utcoffset() is None:
            raise AppError("VALIDATION_ERROR", "审计时间筛选必须包含时区", 422)
    if created_from and created_to and created_from > created_to:
        raise AppError("VALIDATION_ERROR", "created_from 不能晚于 created_to", 422)

    query = db.query(
        AdminAuditLog.id,
        AdminAuditLog.actor_user_id,
        User.email.label("actor_email"),
        AdminAuditLog.action,
        AdminAuditLog.resource_type,
        AdminAuditLog.resource_id,
        AdminAuditLog.reason,
        AdminAuditLog.before_state,
        AdminAuditLog.after_state,
        AdminAuditLog.created_at,
    ).join(User, User.id == AdminAuditLog.actor_user_id)
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
    total = query.order_by(None).count()
    rows = (
        query.order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [
        {
            "id": row.id,
            "actor": {"id": row.actor_user_id, "email": row.actor_email},
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "reason": row.reason,
            "before_state": row.before_state,
            "after_state": row.after_state,
            "created_at": row.created_at,
        }
        for row in rows
    ], total
