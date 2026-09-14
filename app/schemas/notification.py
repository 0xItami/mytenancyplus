from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    title: str
    body: str
    resource_type: str | None
    resource_id: UUID | None
    read_at: datetime | None
    created_at: datetime


class NotificationCountResponse(BaseModel):
    unread: int
