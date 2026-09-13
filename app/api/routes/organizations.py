import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession, Tenant, require_roles
from app.models.audit import OutboxEvent
from app.models.organization import Invitation, Membership, MembershipRole, Organization
from app.schemas.organization import (
    InvitationCreate,
    InvitationResponse,
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
) -> InvitationResponse:
    if payload.role == MembershipRole.OWNER:
        raise HTTPException(status_code=400, detail="Ownership cannot be granted by invitation")

    raw_token = secrets.token_urlsafe(32)
    invitation = Invitation(
        organization_id=tenant.organization_id,
        email=payload.email.lower(),
        role=payload.role,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        invited_by_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(invitation)
    await session.flush()
    session.add(
        OutboxEvent(
            organization_id=tenant.organization_id,
            topic="organization.member_invited",
            payload={"invitation_id": str(invitation.id), "email": invitation.email},
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
    return InvitationResponse.model_validate(invitation)
