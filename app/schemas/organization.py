from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.organization import MembershipRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    created_at: datetime


class OrganizationSummary(OrganizationResponse):
    role: MembershipRole


class InvitationCreate(BaseModel):
    email: EmailStr
    role: MembershipRole = MembershipRole.MANAGER


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    role: MembershipRole
    expires_at: datetime
