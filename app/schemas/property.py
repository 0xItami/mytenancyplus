from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.lease import LeaseStatus


class PropertyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    address_line: str = Field(min_length=4, max_length=300)
    city: str = Field(min_length=2, max_length=100)
    country_code: str = Field(min_length=2, max_length=2)


class PropertyResponse(PropertyCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    created_at: datetime


class UnitCreate(BaseModel):
    property_id: UUID
    label: str = Field(min_length=1, max_length=80)
    bedrooms: int = Field(ge=0, le=100)
    monthly_rent: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)


class UnitResponse(UnitCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    is_active: bool


class TenantCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)


class TenantResponse(TenantCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID


class LeaseCreate(BaseModel):
    unit_id: UUID
    tenant_id: UUID
    starts_on: date
    ends_on: date | None = None
    monthly_rent: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    deposit: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    status: LeaseStatus = LeaseStatus.DRAFT

    @model_validator(mode="after")
    def validate_date_range(self) -> "LeaseCreate":
        if self.ends_on is not None and self.ends_on < self.starts_on:
            raise ValueError("ends_on must not be before starts_on")
        return self


class LeaseResponse(LeaseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
