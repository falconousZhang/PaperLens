import datetime
import uuid

import jwt
import pytest
from pydantic import ValidationError

from paperlens.core.config import Settings, settings
from paperlens.core.deps import require_admin
from paperlens.core.enums import UserRole, UserStatus
from paperlens.core.errors import AppError
from paperlens.models.models import User
from paperlens.services.password_service import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from paperlens.services.token_service import (
    ACCESS_TOKEN_ALGORITHM,
    create_access_token,
    decode_access_token,
)


def test_argon2_password_hash_is_salted_and_verifiable():
    password = "纯文本 Password With Spaces"
    first = hash_password(password)
    second = hash_password(password)
    assert password not in first
    assert first != second
    assert first.startswith("$argon2")
    assert verify_password(password, first)
    assert not verify_password("wrong password", first)
    assert not verify_password(password, None)


def test_jwt_secret_is_required_and_has_no_repository_default(monkeypatch):
    monkeypatch.delenv("PAPERLENS_JWT_SECRET", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
    with pytest.raises(ValidationError):
        Settings(jwt_secret="too-short", _env_file=None)


def test_password_policy_boundaries_and_no_composition_rule():
    fifteen_unicode = "文" * 14 + " "
    assert len(fifteen_unicode) == 15
    assert validate_password_strength(fifteen_unicode) == []
    assert validate_password_strength("x" * 128) == []
    assert validate_password_strength("x" * 14)
    assert validate_password_strength("x" * 129)
    assert validate_password_strength("passwordpassword")
    assert validate_password_strength("SafePaperLensPhrase2026")
    assert validate_password_strength(
        "long.user@example.com",
        email="long.user@example.com",
    )
    assert validate_password_strength("valid length\nnot printable")


def test_access_token_contains_and_requires_security_claims():
    sid = str(uuid.uuid4())
    token, jti = create_access_token("user-1", sid)
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["sid"] == sid
    assert payload["jti"] == jti
    assert payload["typ"] == "access"

    raw_payload = jwt.decode(token, options={"verify_signature": False})
    for claim in ("sub", "sid", "jti", "typ", "iat", "nbf", "exp", "iss", "aud"):
        incomplete = dict(raw_payload)
        incomplete.pop(claim)
        malformed = jwt.encode(
            incomplete,
            settings.jwt_secret.get_secret_value(),
            algorithm=ACCESS_TOKEN_ALGORITHM,
        )
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(malformed)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update(exp=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1)),
        lambda payload: payload.update(nbf=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)),
        lambda payload: payload.update(iss="wrong-issuer"),
        lambda payload: payload.update(aud="wrong-audience"),
        lambda payload: payload.update(typ="refresh"),
        lambda payload: payload.update(sid="not-a-uuid"),
        lambda payload: payload.update(jti="not-a-uuid"),
    ],
)
def test_access_token_rejects_invalid_security_properties(mutation):
    token, _ = create_access_token("user-1", str(uuid.uuid4()))
    payload = jwt.decode(token, options={"verify_signature": False})
    mutation(payload)
    malformed = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=ACCESS_TOKEN_ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(malformed)


def test_access_token_rejects_wrong_signature_and_none_algorithm():
    token, _ = create_access_token("user-1", str(uuid.uuid4()))
    payload = jwt.decode(token, options={"verify_signature": False})
    wrong_signature = jwt.encode(
        payload,
        "different-test-secret-that-is-also-long-enough-2026",
        algorithm=ACCESS_TOKEN_ALGORITHM,
    )
    unsigned = jwt.encode(payload, key="", algorithm="none")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(wrong_signature)
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(unsigned)


def test_require_admin_uses_current_user_role():
    user = User(
        id="user-role-test",
        email="role@example.com",
        email_normalized="role@example.com",
        display_name="Role Test",
        password_hash="not-used",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )
    with pytest.raises(AppError) as error:
        require_admin(user)
    assert error.value.status_code == 403

    user.role = UserRole.ADMIN
    assert require_admin(user) is user
