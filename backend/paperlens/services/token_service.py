from __future__ import annotations

import datetime
import uuid

import jwt

from paperlens.core.config import settings

ACCESS_TOKEN_ALGORITHM = "HS256"
_REQUIRED_CLAIMS = ("sub", "sid", "jti", "typ", "iat", "nbf", "exp", "iss", "aud")


def create_access_token(
    sub: str,
    sid: str,
    jti: str | None = None,
) -> tuple[str, str]:
    if jti is None:
        jti = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": sub,
        "sid": sid,
        "jti": jti,
        "typ": "access",
        "iat": now,
        "nbf": now,
        "exp": now + datetime.timedelta(minutes=settings.jwt_access_ttl_minutes),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=ACCESS_TOKEN_ALGORITHM,
    )
    return token, jti


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[ACCESS_TOKEN_ALGORITHM],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": list(_REQUIRED_CLAIMS)},
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("not an access token")
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject or len(subject) > 128:
        raise jwt.InvalidTokenError("invalid subject")
    for claim in ("sid", "jti"):
        value = payload.get(claim)
        if not isinstance(value, str):
            raise jwt.InvalidTokenError(f"invalid {claim}")
        try:
            uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise jwt.InvalidTokenError(f"invalid {claim}") from exc
    return payload
