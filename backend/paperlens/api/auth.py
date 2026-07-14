from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.orm import Session

from paperlens.core.config import settings
from paperlens.core.database import get_db
from paperlens.core.deps import get_current_auth_context, get_current_user
from paperlens.core.errors import AppError
from paperlens.models.models import User
from paperlens.schemas.auth import (
    AuthTokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UserResponse,
)
from paperlens.services import auth_service


router = APIRouter(prefix="/auth", tags=["auth"])
_REFRESH_COOKIE_NAME = "paperlens_refresh"


def _public_user(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
    )


def _token_response(user: User, access_token: str) -> AuthTokenResponse:
    return AuthTokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_ttl_minutes * 60,
        user=_public_user(user),
    )


@router.post("/register", response_model=AuthTokenResponse, status_code=201)
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.register_user(db, body.email, body.password, body.display_name)
    access_token, refresh_token = auth_service.create_session_for_user(db, user)
    db.commit()
    _set_refresh_cookie(response, refresh_token)
    return _token_response(user, access_token)


@router.post("/login", response_model=AuthTokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user, access_token, refresh_token = auth_service.authenticate_user(
        db,
        body.email,
        body.password,
    )
    db.commit()
    _set_refresh_cookie(response, refresh_token)
    return _token_response(user, access_token)


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise AppError(
            "INVALID_REFRESH_TOKEN",
            "无效的认证凭据",
            401,
            headers={"WWW-Authenticate": "Bearer"},
        )
    user, access_token, new_refresh = auth_service.refresh_session(db, refresh_token)
    db.commit()
    _set_refresh_cookie(response, new_refresh)
    return _token_response(user, access_token)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    context: auth_service.AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
):
    auth_service.logout_family(db, context)
    db.commit()
    _clear_refresh_cookie(response)
    return MessageResponse(message="已退出登录")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(
    response: Response,
    context: auth_service.AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
):
    auth_service.logout_all_sessions(db, context.user.id)
    db.commit()
    _clear_refresh_cookie(response)
    return MessageResponse(message="已退出所有设备")


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return _public_user(user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = auth_service.update_profile(db, user, display_name=body.display_name)
    db.commit()
    return _public_user(updated)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    body: ChangePasswordRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service.change_password(db, user, body.old_password, body.new_password)
    db.commit()
    _clear_refresh_cookie(response)
    return MessageResponse(message="密码已修改，请重新登录")


@router.post("/forgot-password", response_model=MessageResponse, status_code=202)
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    reset_notifier: auth_service.PasswordResetNotifier = Depends(
        auth_service.get_password_reset_notifier
    ),
):
    auth_service.request_password_reset(db, body.email, reset_notifier)
    db.commit()
    return MessageResponse(
        message="若账号存在且通知服务可用，将发送密码重置指引"
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, body.token, body.new_password)
    db.commit()
    return MessageResponse(message="密码已重置，请重新登录")


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.jwt_refresh_ttl_days * 24 * 3600,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )
