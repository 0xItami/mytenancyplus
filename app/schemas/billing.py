from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.billing import SubscriptionPlan, SubscriptionStatus


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    provider: str
    plan: SubscriptionPlan
    status: SubscriptionStatus
    current_period_end: datetime | None
    cancel_at_period_end: bool


class WebhookResponse(BaseModel):
    accepted: bool = True
    duplicate: bool
    event_id: str
