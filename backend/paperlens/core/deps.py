from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from paperlens.core.database import get_db
from paperlens.core.enums import UserRole
from paperlens.core.errors import AppError
from paperlens.models.models import User
from paperlens.services import auth_service

_bearer = HTTPBearer(auto_error=False)


def get_current_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> auth_service.AuthContext:
    if credentials is None:
        raise AppError(
            "UNAUTHORIZED",
            "无效的认证凭据",
            401,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_service.get_auth_context_from_token(db, credentials.credentials)


def get_current_user(
    context: auth_service.AuthContext = Depends(get_current_auth_context),
) -> User:
    return context.user


def get_current_user_id(
    user: User = Depends(get_current_user),
) -> str:
    return user.id


def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != UserRole.ADMIN:
        raise AppError("FORBIDDEN", "需要管理员权限", 403)
    return user
