from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"


class InvalidTokenError(ValueError):
    """Raised when an access token is invalid or expired."""


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_password: str) -> bool:
    return password_hash.verify(password, encoded_password)


def create_access_token(user_id: UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise InvalidTokenError("Unexpected token type")
        return UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenError("Invalid or expired access token") from exc


def create_invitation_token(
    *,
    invitation_id: UUID,
    organization_id: UUID,
    token_id: str,
    email: str,
    expires_at: datetime,
    settings: Settings,
) -> str:
    payload: dict[str, Any] = {
        "sub": str(invitation_id),
        "organization_id": str(organization_id),
        "jti": token_id,
        "email": email,
        "exp": expires_at,
        "type": "invitation",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_invitation_token(token: str, settings: Settings) -> tuple[UUID, UUID, str, str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        if payload.get("type") != "invitation":
            raise InvalidTokenError("Unexpected token type")
        return (
            UUID(payload["sub"]),
            UUID(payload["organization_id"]),
            str(payload["jti"]),
            str(payload["email"]),
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenError("Invalid or expired invitation token") from exc
