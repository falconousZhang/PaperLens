from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from paperlens.core.config import settings
from paperlens.core.enums import UserRole, UserStatus
from paperlens.core.errors import AppError
from paperlens.models.models import AuthSession, PasswordResetToken, User
from paperlens.services.password_service import (
    generate_token,
    hash_password,
    hash_token,
    perform_dummy_password_check,
    validate_password_strength,
    verify_password,
)
from paperlens.services.token_service import create_access_token, decode_access_token


class PasswordResetNotifier(Protocol):
    def send(self, user: User, reset_token: str) -> None: ...


class NullPasswordResetNotifier:
    def send(self, user: User, reset_token: str) -> None:
        return None


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession


_default_notifier = NullPasswordResetNotifier()


def get_password_reset_notifier() -> PasswordResetNotifier:
    return _default_notifier


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _unauthorized(code: str = "INVALID_CREDENTIALS", message: str = "邮箱或密码错误") -> AppError:
    return AppError(
        code,
        message,
        401,
        headers={"WWW-Authenticate": "Bearer"},
    )


def register_user(
    db: Session,
    email: str,
    password: str,
    display_name: str,
) -> User:
    email_value = email.strip()
    email_normalized = email_value.casefold()
    name = display_name.strip()
    if not name:
        raise AppError("VALIDATION_ERROR", "显示名称不能为空", 422)

    errors = validate_password_strength(password, email=email_value)
    if errors:
        raise AppError("WEAK_PASSWORD", "; ".join(errors), 422)

    existing = db.query(User.id).filter(User.email_normalized == email_normalized).first()
    if existing:
        raise AppError("EMAIL_EXISTS", "该邮箱已注册", 409)

    user = User(
        id=str(uuid.uuid4()),
        email=email_value,
        email_normalized=email_normalized,
        display_name=name,
        password_hash=hash_password(password),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError("EMAIL_EXISTS", "该邮箱已注册", 409) from exc
    return user


def create_session_for_user(db: Session, user: User) -> tuple[str, str]:
    family_id = str(uuid.uuid4())
    refresh_token, session = _create_session(db, user.id, family_id)
    access_token, _ = create_access_token(sub=user.id, sid=session.sid)
    return access_token, refresh_token


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> tuple[User, str, str]:
    email_normalized = email.strip().casefold()
    user = (
        db.query(User)
        .filter(User.email_normalized == email_normalized)
        .with_for_update()
        .first()
    )
    now = _utcnow()

    if user is None:
        perform_dummy_password_check(password)
        raise _unauthorized()

    if user.status != UserStatus.ACTIVE or not user.password_hash:
        perform_dummy_password_check(password)
        raise _unauthorized()

    if user.locked_until and user.locked_until > now:
        perform_dummy_password_check(password)
        raise _unauthorized()

    if user.locked_until and user.locked_until <= now:
        user.failed_login_count = 0
        user.locked_until = None

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.auth_max_failed_logins:
            user.locked_until = now + datetime.timedelta(minutes=settings.auth_lockout_minutes)
        db.commit()
        raise _unauthorized()

    user.failed_login_count = 0
    user.locked_until = None
    db.flush()
    access_token, refresh_token = create_session_for_user(db, user)
    return user, access_token, refresh_token


def _create_session(
    db: Session,
    user_id: str,
    family_id: str,
) -> tuple[str, AuthSession]:
    raw_token = generate_token()
    now = _utcnow()
    session = AuthSession(
        sid=str(uuid.uuid4()),
        family_id=family_id,
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=now + datetime.timedelta(days=settings.jwt_refresh_ttl_days),
        created_at=now,
        last_used_at=now,
    )
    db.add(session)
    db.flush()
    return raw_token, session


def refresh_session(
    db: Session,
    raw_refresh_token: str,
) -> tuple[User, str, str]:
    token_digest = hash_token(raw_refresh_token)
    session = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == token_digest)
        .with_for_update()
        .first()
    )
    now = _utcnow()

    if session is None:
        raise _unauthorized("INVALID_REFRESH_TOKEN", "无效的认证凭据")

    if session.revoked_at is not None:
        _revoke_family(db, session.family_id, "refresh_replay")
        db.commit()
        raise _unauthorized("INVALID_REFRESH_TOKEN", "无效的认证凭据")

    if session.expires_at <= now:
        _revoke_session(session, "expired", now)
        db.commit()
        raise _unauthorized("INVALID_REFRESH_TOKEN", "无效的认证凭据")

    user = db.get(User, session.user_id)
    if (
        user is None
        or user.status != UserStatus.ACTIVE
        or not user.password_hash
        or (user.locked_until is not None and user.locked_until > now)
    ):
        _revoke_family(db, session.family_id, "user_unavailable")
        db.commit()
        raise _unauthorized("INVALID_REFRESH_TOKEN", "无效的认证凭据")

    _revoke_session(session, "replaced", now)
    session.last_used_at = now
    new_raw, new_session = _create_session(db, user.id, session.family_id)
    session.replaced_by_id = new_session.sid
    db.flush()

    access_token, _ = create_access_token(sub=user.id, sid=new_session.sid)
    return user, access_token, new_raw


def _revoke_session(
    session: AuthSession,
    reason: str,
    now: datetime.datetime | None = None,
) -> None:
    if session.revoked_at is None:
        session.revoked_at = now or _utcnow()
        session.revoke_reason = reason


def _revoke_family(db: Session, family_id: str, reason: str) -> None:
    now = _utcnow()
    sessions = (
        db.query(AuthSession)
        .filter(AuthSession.family_id == family_id, AuthSession.revoked_at.is_(None))
        .all()
    )
    for session in sessions:
        _revoke_session(session, reason, now)
    db.flush()


def logout_family(db: Session, context: AuthContext) -> None:
    _revoke_family(db, context.session.family_id, "logout")


def logout_all_sessions(db: Session, user_id: str, reason: str = "logout_all") -> None:
    now = _utcnow()
    sessions = db.query(AuthSession).filter(
        AuthSession.user_id == user_id,
        AuthSession.revoked_at.is_(None),
    ).all()
    for session in sessions:
        _revoke_session(session, reason, now)
    db.flush()


def get_auth_context_from_token(db: Session, access_token: str) -> AuthContext:
    try:
        payload = decode_access_token(access_token)
    except Exception as exc:
        raise _unauthorized("INVALID_TOKEN", "无效的认证凭据") from exc

    user_id = payload["sub"]
    sid = payload["sid"]
    now = _utcnow()
    session = db.get(AuthSession, sid)
    if (
        session is None
        or session.user_id != user_id
        or session.revoked_at is not None
        or session.expires_at <= now
    ):
        raise _unauthorized("INVALID_TOKEN", "无效的认证凭据")

    user = db.get(User, user_id)
    if (
        user is None
        or user.status != UserStatus.ACTIVE
        or not user.password_hash
        or (user.locked_until is not None and user.locked_until > now)
    ):
        raise _unauthorized("INVALID_TOKEN", "无效的认证凭据")

    return AuthContext(user=user, session=session)


def get_current_user_from_token(db: Session, access_token: str) -> User:
    return get_auth_context_from_token(db, access_token).user


def change_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    locked_user = db.query(User).filter(User.id == user.id).with_for_update().one()
    if not verify_password(current_password, locked_user.password_hash):
        raise _unauthorized()

    errors = validate_password_strength(new_password, email=locked_user.email)
    if errors:
        raise AppError("WEAK_PASSWORD", "; ".join(errors), 422)

    locked_user.password_hash = hash_password(new_password)
    locked_user.password_changed_at = _utcnow()
    locked_user.failed_login_count = 0
    locked_user.locked_until = None
    logout_all_sessions(db, locked_user.id, "password_changed")


def request_password_reset(
    db: Session,
    email: str,
    reset_notifier: PasswordResetNotifier,
) -> None:
    raw_token = generate_token()
    token_digest = hash_token(raw_token)
    email_normalized = email.strip().casefold()
    user = (
        db.query(User)
        .filter(User.email_normalized == email_normalized)
        .with_for_update()
        .first()
    )
    if user is None or user.status != UserStatus.ACTIVE or not user.password_hash:
        return

    now = _utcnow()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)
    reset = PasswordResetToken(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=token_digest,
        expires_at=now + datetime.timedelta(minutes=settings.jwt_reset_ttl_minutes),
        created_at=now,
    )
    db.add(reset)
    db.flush()
    reset_notifier.send(user, raw_token)


def reset_password(
    db: Session,
    raw_token: str,
    new_password: str,
) -> None:
    token_digest = hash_token(raw_token)
    reset = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_digest)
        .with_for_update()
        .first()
    )
    now = _utcnow()
    if reset is None or reset.used_at is not None:
        raise AppError("INVALID_RESET_TOKEN", "无效或已失效的重置令牌", 400)
    if reset.expires_at <= now:
        reset.used_at = now
        db.commit()
        raise AppError("INVALID_RESET_TOKEN", "无效或已失效的重置令牌", 400)

    user = db.query(User).filter(User.id == reset.user_id).with_for_update().first()
    if user is None or user.status != UserStatus.ACTIVE or not user.password_hash:
        reset.used_at = now
        db.commit()
        raise AppError("INVALID_RESET_TOKEN", "无效或已失效的重置令牌", 400)

    errors = validate_password_strength(new_password, email=user.email)
    if errors:
        raise AppError("WEAK_PASSWORD", "; ".join(errors), 422)

    user.password_hash = hash_password(new_password)
    user.password_changed_at = now
    user.failed_login_count = 0
    user.locked_until = None
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)
    logout_all_sessions(db, user.id, "password_reset")


def update_profile(
    db: Session,
    user: User,
    display_name: str | None = None,
) -> User:
    if display_name is not None:
        name = display_name.strip()
        if not name:
            raise AppError("VALIDATION_ERROR", "显示名称不能为空", 422)
        user.display_name = name
    db.flush()
    return user
