import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.session import RefreshSession


class InvalidRefreshTokenError(ValueError):
    pass


class RefreshTokenReuseError(InvalidRefreshTokenError):
    pass


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _parse_token(token: str) -> tuple[UUID, str]:
    try:
        session_id, secret = token.split(".", maxsplit=1)
        return UUID(session_id), secret
    except (ValueError, AttributeError) as exc:
        raise InvalidRefreshTokenError("Malformed refresh token") from exc


def create_refresh_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    settings: Settings,
    family_id: UUID | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[RefreshSession, str]:
    session_id = uuid4()
    raw_secret = secrets.token_urlsafe(48)
    refresh_session = RefreshSession(
        id=session_id,
        user_id=user_id,
        family_id=family_id or uuid4(),
        secret_hash=_hash_secret(raw_secret),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days),
        user_agent=(user_agent or "")[:500] or None,
        ip_address=(ip_address or "")[:64] or None,
    )
    session.add(refresh_session)
    return refresh_session, f"{session_id}.{raw_secret}"


async def rotate_refresh_token(
    session: AsyncSession,
    *,
    token: str,
    settings: Settings,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[RefreshSession, str]:
    session_id, secret = _parse_token(token)
    current = await session.get(RefreshSession, session_id, with_for_update=True)
    if current is None or not hmac.compare_digest(current.secret_hash, _hash_secret(secret)):
        raise InvalidRefreshTokenError("Unknown refresh token")
    now = datetime.now(UTC)
    if current.revoked_at is not None:
        await session.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == current.family_id)
            .values(revoked_at=now)
        )
        await session.commit()
        raise RefreshTokenReuseError("Refresh token reuse detected")
    if _as_utc(current.expires_at) <= now:
        current.revoked_at = now
        await session.commit()
        raise InvalidRefreshTokenError("Expired refresh token")

    replacement, raw_token = create_refresh_session(
        session,
        user_id=current.user_id,
        settings=settings,
        family_id=current.family_id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    current.revoked_at = now
    current.last_used_at = now
    current.replaced_by_id = replacement.id
    await session.commit()
    return replacement, raw_token


async def revoke_refresh_token(session: AsyncSession, token: str) -> None:
    session_id, secret = _parse_token(token)
    current = await session.get(RefreshSession, session_id, with_for_update=True)
    if current is None or not hmac.compare_digest(current.secret_hash, _hash_secret(secret)):
        return
    current.revoked_at = datetime.now(UTC)
    await session.commit()
