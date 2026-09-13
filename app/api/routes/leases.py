from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession, Tenant, require_roles
from app.models.lease import Lease, LeaseStatus, TenantProfile
from app.models.organization import MembershipRole
from app.models.property import Unit
from app.schemas.property import LeaseCreate, LeaseResponse, TenantCreate, TenantResponse
from app.services.audit import record_audit_event
from app.services.leases import has_overlapping_active_lease

router = APIRouter()
write_roles = require_roles(MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.MANAGER)


@router.post(
    "/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[write_roles],
)
async def create_tenant(
    payload: TenantCreate,
    session: DatabaseSession,
    tenant: Tenant,
) -> TenantProfile:
    profile = TenantProfile(
        organization_id=tenant.organization_id,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=payload.email.lower(),
        phone=payload.phone,
    )
    session.add(profile)
    await session.commit()
    return profile


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(session: DatabaseSession, tenant: Tenant) -> list[TenantProfile]:
    result = await session.scalars(
        select(TenantProfile)
        .where(TenantProfile.organization_id == tenant.organization_id)
        .order_by(TenantProfile.last_name, TenantProfile.first_name)
    )
    return list(result.all())


@router.post(
    "/leases",
    response_model=LeaseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[write_roles],
)
async def create_lease(
    payload: LeaseCreate,
    session: DatabaseSession,
    user: CurrentUser,
    tenant: Tenant,
) -> Lease:
    unit = await session.scalar(
        select(Unit).where(
            Unit.id == payload.unit_id,
            Unit.organization_id == tenant.organization_id,
        )
    )
    tenant_profile = await session.scalar(
        select(TenantProfile).where(
            TenantProfile.id == payload.tenant_id,
            TenantProfile.organization_id == tenant.organization_id,
        )
    )
    if unit is None or tenant_profile is None:
        raise HTTPException(status_code=404, detail="Unit or tenant not found")
    if payload.status == LeaseStatus.ACTIVE and await has_overlapping_active_lease(
        session,
        organization_id=tenant.organization_id,
        unit_id=payload.unit_id,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
    ):
        raise HTTPException(status_code=409, detail="Unit already has an overlapping active lease")

    lease = Lease(organization_id=tenant.organization_id, **payload.model_dump())
    session.add(lease)
    await session.flush()
    record_audit_event(
        session,
        organization_id=tenant.organization_id,
        actor_user_id=user.id,
        action="lease.created",
        resource_type="lease",
        resource_id=lease.id,
        details={"status": lease.status.value},
    )
    await session.commit()
    return lease


@router.get("/leases", response_model=list[LeaseResponse])
async def list_leases(session: DatabaseSession, tenant: Tenant) -> list[Lease]:
    result = await session.scalars(
        select(Lease)
        .where(Lease.organization_id == tenant.organization_id)
        .order_by(Lease.starts_on.desc())
    )
    return list(result.all())
