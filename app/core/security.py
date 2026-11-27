"""Password hashing and JWT access-token helpers.

The application issues short-lived HS256 access tokens. Passwords are
hashed with Argon2id through argon2-cffi; plaintext passwords are never
stored, logged, or returned by the API.
"""

from datetime import datetime, timedelta, timezone
import secrets
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from app.core import config


ALLOWED_ROLES = {"admin", "employee"}
TOKEN_TYPE = "access"

_password_hasher = PasswordHasher()

# A process-local fallback keeps local development and tests usable when
# JWT_SECRET is not configured. Tokens become invalid on restart and are
# not shared between workers, so deployments must set JWT_SECRET.
_ephemeral_secret = secrets.token_urlsafe(48)


class TokenError(ValueError):
    """Raised when an access token is missing, invalid, or expired."""


def _jwt_secret() -> str:
    return config.JWT_SECRET or _ephemeral_secret


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password must not be empty")

    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False

    try:
        return _password_hasher.verify(password_hash, password)
    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
    ):
        return False


def create_access_token(
    *,
    employee_id: str,
    role: str,
    expires_minutes: int | None = None,
) -> str:
    if role not in ALLOWED_ROLES:
        raise ValueError(f"unsupported role: {role}")

    now = datetime.now(timezone.utc)
    ttl = (
        expires_minutes
        if expires_minutes is not None
        else config.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": employee_id,
        "role": role,
        "type": TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl)).timestamp()),
    }

    return jwt.encode(
        payload,
        _jwt_secret(),
        algorithm=config.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    if not token:
        raise TokenError("missing token")

    try:
        payload = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[config.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "role", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("invalid token") from exc

    if payload.get("type") != TOKEN_TYPE:
        raise TokenError("invalid token type")

    role = payload.get("role")
    if role not in ALLOWED_ROLES:
        raise TokenError("invalid role claim")

    employee_id = payload.get("sub")
    if not isinstance(employee_id, str) or not employee_id:
        raise TokenError("invalid subject claim")

    return payload
