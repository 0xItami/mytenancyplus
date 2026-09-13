from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class LeaseStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"


class TenantProfile(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_profiles"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))


class Lease(UUIDPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "leases"

    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"), index=True, nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant_profiles.id"), index=True, nullable=False
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date)
    monthly_rent: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    deposit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[LeaseStatus] = mapped_column(
        Enum(LeaseStatus, native_enum=False), default=LeaseStatus.DRAFT, nullable=False
    )
