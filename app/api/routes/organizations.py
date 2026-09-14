import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text

from app.api.dependencies import CurrentUser, DatabaseSession, Tenant, require_roles
from app.core.config import Settings, get_settings
from app.core.security import InvalidTokenError, create_invitation_token, decode_invitation_token
from app.models.audit import OutboxEvent
from app.models.organization import (
    Invitation,
    Membership,
    MembershipRole,
    MembershipStatus,
    Organization,
)
from app.models.user import User
from app.schemas.organization import (
    InvitationAcceptRequest,
    InvitationCreate,
    InvitationResponse,
    MembershipDetailResponse,
    MembershipResponse,
    OrganizationCreate,
    OrganizationSummary,
)
from app.services.audit import record_audit_event

router = APIRouter()


def build_slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "organization"
    return f"{base[:88]}-{secrets.token_hex(3)}"


@router.post("", response_model=OrganizationSummary, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate, session: DatabaseSession, user: CurrentUser
) -> OrganizationSummary:
    organization = Organization(
        name=payload.name.strip(),
        slug=build_slug(payload.name),
        created_by_id=user.id,
    )
    session.add(organization)
    await session.flush()
    session.add(
        Membership(
            organization_id=organization.id,
            user_id=user.id,
            role=MembershipRole.OWNER,
        )
    )
    await session.commit()
    await session.refresh(organization)
    return OrganizationSummary(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        created_at=organization.created_at,
        role=MembershipRole.OWNER,
    )


@router.get("", response_model=list[OrganizationSummary])
async def list_organizations(
    session: DatabaseSession, user: CurrentUser
) -> list[OrganizationSummary]:
    result = await session.execute(
        select(Organization, Membership.role)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id)
        .order_by(Organization.name)
    )
    return [
        OrganizationSummary(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            created_at=organization.created_at,
            role=role,
        )
        for organization, role in result.all()
    ]


@router.get("/members", response_model=list[MembershipDetailResponse])
async def list_members(session: DatabaseSession, tenant: Tenant) -> list[MembershipDetailResponse]:
    result = await session.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == tenant.organization_id)
        .order_by(User.full_name)
    )
    return [
        MembershipDetailResponse(
            organization_id=membership.organization_id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
            status=membership.status,
        )
        for membership, user in result.all()
    ]


@router.post(
    "/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[require_roles(MembershipRole.OWNER, MembershipRole.ADMIN)],
)
async def invite_member(
    payload: InvitationCreate,
    session: DatabaseSession,
    user: CurrentUser,
    tenant: Tenant,
    settings: Annotated[Settings, Depends(get_settings)],
) -> InvitationResponse:
    if payload.role == MembershipRole.OWNER:
        raise HTTPException(status_code=400, detail="Ownership cannot be granted by invitation")

    token_id = secrets.token_urlsafe(32)
    invitation = Invitation(
        organization_id=tenant.organization_id,
        email=payload.email.lower(),
        role=payload.role,
        token_hash=hashlib.sha256(token_id.encode()).hexdigest(),
        invited_by_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(invitation)
    await session.flush()
    session.add(
        OutboxEvent(
            organization_id=tenant.organization_id,
            topic="organization.member_invited",
            payload={
                "invitation_id": str(invitation.id),
                "organization_id": str(tenant.organization_id),
                "email": invitation.email,
                "token_id": token_id,
                "expires_at": invitation.expires_at.isoformat(),
            },
        )
    )
    record_audit_event(
        session,
        organization_id=tenant.organization_id,
        actor_user_id=user.id,
        action="invitation.created",
        resource_type="invitation",
        resource_id=invitation.id,
        details={"email": invitation.email, "role": invitation.role.value},
    )
    await session.commit()
    delivery_token = None
    if settings.environment in {"local", "test"}:
        delivery_token = create_invitation_token(
            invitation_id=invitation.id,
            organization_id=tenant.organization_id,
            token_id=token_id,
            email=invitation.email,
            expires_at=invitation.expires_at,
            settings=settings,
        )
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        expires_at=invitation.expires_at,
        delivery_token=delivery_token,
    )


@router.post("/invitations/accept", response_model=MembershipResponse)
async def accept_invitation(
    payload: InvitationAcceptRequest,
    session: DatabaseSession,
    user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> MembershipResponse:
    try:
        invitation_id, organization_id, token_id, invited_email = decode_invitation_token(
            payload.token, settings
        )
    except InvalidTokenError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if user.email.lower() != invited_email.lower():
        raise HTTPException(status_code=403, detail="Invitation belongs to another email")
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        await session.execute(
            text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
            {"organization_id": str(organization_id)},
        )
    invitation = await session.scalar(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.organization_id == organization_id,
        )
    )
    now = datetime.now(UTC)
    expires_at = None
    if invitation is not None:
        expires_at = invitation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
    if invitation is None or invitation.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Invitation is unavailable")
    if expires_at is None or expires_at <= now:
        raise HTTPException(status_code=400, detail="Invitation is unavailable")
    if not secrets.compare_digest(
        invitation.token_hash, hashlib.sha256(token_id.encode()).hexdigest()
    ):
        raise HTTPException(status_code=400, detail="Invitation token is invalid")

    membership = await session.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user.id,
        )
    )
    if membership is None:
        membership = Membership(
            organization_id=organization_id,
            user_id=user.id,
            role=invitation.role,
        )
        session.add(membership)
    else:
        membership.role = invitation.role
        membership.status = MembershipStatus.ACTIVE
    invitation.accepted_at = now
    session.add(
        OutboxEvent(
            organization_id=organization_id,
            topic="organization.member_joined",
            payload={"user_id": str(user.id), "role": invitation.role.value},
        )
    )
    await session.commit()
    return MembershipResponse(
        organization_id=organization_id,
        user_id=user.id,
        role=membership.role,
    )
