from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.params import Depends as DependsParam
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models.organization import Membership, MembershipRole, MembershipStatus
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(token, settings)
    except InvalidTokenError as exc:
        raise credentials_error from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass(frozen=True)
class TenantContext:
    organization_id: UUID
    user_id: UUID
    role: MembershipRole


async def get_tenant_context(
    session: DatabaseSession,
    user: CurrentUser,
    organization_id: Annotated[UUID, Header(alias="X-Organization-ID")],
) -> TenantContext:
    membership = await session.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user.id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied"
        )

    if session.bind is not None and session.bind.dialect.name == "postgresql":
        await session.execute(
            text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
            {"organization_id": str(organization_id)},
        )
    return TenantContext(organization_id=organization_id, user_id=user.id, role=membership.role)


Tenant = Annotated[TenantContext, Depends(get_tenant_context)]


def require_roles(*roles: MembershipRole) -> DependsParam:
    async def authorize(context: Tenant) -> TenantContext:
        if context.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your organization role does not permit this action",
            )
        return context

    return DependsParam(dependency=authorize)
