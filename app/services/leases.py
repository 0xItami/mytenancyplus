from datetime import date
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lease import Lease, LeaseStatus


def date_ranges_overlap(
    first_start: date,
    first_end: date | None,
    second_start: date,
    second_end: date | None,
) -> bool:
    """Return whether two inclusive date ranges overlap; None means unbounded."""

    return (first_end is None or second_start <= first_end) and (
        second_end is None or first_start <= second_end
    )


def overlapping_lease_query(
    *, organization_id: UUID, unit_id: UUID, starts_on: date, ends_on: date | None
) -> Select[tuple[Lease]]:
    query = select(Lease).where(
        Lease.organization_id == organization_id,
        Lease.unit_id == unit_id,
        Lease.status == LeaseStatus.ACTIVE,
        or_(Lease.ends_on.is_(None), Lease.ends_on >= starts_on),
    )
    if ends_on is not None:
        query = query.where(Lease.starts_on <= ends_on)
    return query


async def has_overlapping_active_lease(
    session: AsyncSession,
    *,
    organization_id: UUID,
    unit_id: UUID,
    starts_on: date,
    ends_on: date | None,
) -> bool:
    result = await session.execute(
        overlapping_lease_query(
            organization_id=organization_id,
            unit_id=unit_id,
            starts_on=starts_on,
            ends_on=ends_on,
        )
    )
    return result.scalar_one_or_none() is not None
