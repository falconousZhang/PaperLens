from __future__ import annotations

import hashlib
import secrets

from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()
_dummy_hash = _hasher.hash("paperlens-dummy-verification-value-never-authenticates")
_common_passwords = {
    "password",
    "password1",
    "password123",
    "passwordpassword",
    "123456789012345",
    "qwertyqwertyqwe",
    "letmeinletmein123",
    "correcthorsebatterystaple",
    "adminadminadmin",
    "welcome123456789",
}


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password, password_hash)
    except Exception:
        return False


def perform_dummy_password_check(password: str) -> None:
    verify_password(password, _dummy_hash)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def is_password_breached(password: str) -> bool:
    return password.casefold() in _common_passwords


def validate_password_strength(password: str, *, email: str | None = None) -> list[str]:
    errors: list[str] = []
    code_points = len(password)
    if code_points < 15:
        errors.append(f"密码至少需要 15 个字符（当前 {code_points} 个）")
    if code_points > 128:
        errors.append("密码不能超过 128 个字符")
    if password and not password.isprintable():
        errors.append("密码只能包含可打印 Unicode 字符")
    if is_password_breached(password):
        errors.append("该密码过于常见，请选择更强的密码")
    folded = password.casefold()
    if "paperlens" in folded:
        errors.append("密码不能包含项目名称")
    if email and folded == email.strip().casefold():
        errors.append("密码不能与邮箱相同")
    return errors
