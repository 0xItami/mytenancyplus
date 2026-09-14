from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    details: dict[str, object]
    created_at: datetime
