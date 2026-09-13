from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession, Tenant, require_roles
from app.models.organization import MembershipRole
from app.models.property import Property, Unit
from app.schemas.property import PropertyCreate, PropertyResponse, UnitCreate, UnitResponse
from app.services.audit import record_audit_event

router = APIRouter()
write_roles = require_roles(MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.MANAGER)


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[write_roles],
)
async def create_property(
    payload: PropertyCreate,
    session: DatabaseSession,
    user: CurrentUser,
    tenant: Tenant,
) -> Property:
    property_ = Property(
        organization_id=tenant.organization_id,
        name=payload.name.strip(),
        address_line=payload.address_line.strip(),
        city=payload.city.strip(),
        country_code=payload.country_code.upper(),
    )
    session.add(property_)
    await session.flush()
    record_audit_event(
        session,
        organization_id=tenant.organization_id,
        actor_user_id=user.id,
        action="property.created",
        resource_type="property",
        resource_id=property_.id,
    )
    await session.commit()
    return property_


@router.get("", response_model=list[PropertyResponse])
async def list_properties(session: DatabaseSession, tenant: Tenant) -> list[Property]:
    result = await session.scalars(
        select(Property)
        .where(Property.organization_id == tenant.organization_id)
        .order_by(Property.name)
    )
    return list(result.all())


@router.post(
    "/units",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[write_roles],
)
async def create_unit(payload: UnitCreate, session: DatabaseSession, tenant: Tenant) -> Unit:
    property_ = await session.scalar(
        select(Property).where(
            Property.id == payload.property_id,
            Property.organization_id == tenant.organization_id,
        )
    )
    if property_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    unit = Unit(
        organization_id=tenant.organization_id,
        property_id=payload.property_id,
        label=payload.label.strip(),
        bedrooms=payload.bedrooms,
        monthly_rent=payload.monthly_rent,
        currency=payload.currency.upper(),
    )
    session.add(unit)
    await session.commit()
    return unit


@router.get("/units", response_model=list[UnitResponse])
async def list_units(session: DatabaseSession, tenant: Tenant) -> list[Unit]:
    result = await session.scalars(
        select(Unit).where(Unit.organization_id == tenant.organization_id).order_by(Unit.label)
    )
    return list(result.all())
