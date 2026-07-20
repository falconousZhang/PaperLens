from __future__ import annotations

import hashlib
import secrets

from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()
_dummy_hash = _hasher.hash("paperlens-dummy-verification-value-never-authenticates")


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


def validate_password_strength(password: str, *, email: str | None = None) -> list[str]:
    errors: list[str] = []
    code_points = len(password)
    if code_points < 8:
        errors.append(f"密码至少需要 8 个字符（当前 {code_points} 个）")
    if code_points > 128:
        errors.append("密码不能超过 128 个字符")
    return errors
