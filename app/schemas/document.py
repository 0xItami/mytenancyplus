from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    resource_type: str
    resource_id: UUID
    uploaded_by_id: UUID
    created_at: datetime
