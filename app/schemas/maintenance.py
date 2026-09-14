from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.maintenance import WorkOrderPriority, WorkOrderStatus


class WorkOrderCreate(BaseModel):
    property_id: UUID
    unit_id: UUID | None = None
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=5, max_length=10_000)
    priority: WorkOrderPriority = WorkOrderPriority.NORMAL
    assigned_to_id: UUID | None = None
    due_at: datetime | None = None


class WorkOrderUpdate(BaseModel):
    status: WorkOrderStatus | None = None
    priority: WorkOrderPriority | None = None
    assigned_to_id: UUID | None = None
    due_at: datetime | None = None


class WorkOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    property_id: UUID
    unit_id: UUID | None
    title: str
    description: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    reported_by_id: UUID
    assigned_to_id: UUID | None
    due_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkOrderCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class WorkOrderCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_id: UUID
    author_user_id: UUID
    body: str
    created_at: datetime
