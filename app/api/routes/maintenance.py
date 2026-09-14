from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession, Tenant, require_roles
from app.models.maintenance import WorkOrder, WorkOrderComment, WorkOrderStatus
from app.models.organization import Membership, MembershipRole, MembershipStatus
from app.models.property import Property, Unit
from app.schemas.maintenance import (
    WorkOrderCommentCreate,
    WorkOrderCommentResponse,
    WorkOrderCreate,
    WorkOrderResponse,
    WorkOrderUpdate,
)
from app.services.audit import record_audit_event
from app.services.maintenance import InvalidWorkOrderTransition, transition_work_order
from app.services.notifications import create_notification

router = APIRouter()
write_roles = require_roles(MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.MANAGER)


async def find_work_order(
    session: DatabaseSession, tenant: Tenant, work_order_id: UUID
) -> WorkOrder:
    work_order = await session.scalar(
        select(WorkOrder).where(
            WorkOrder.id == work_order_id,
            WorkOrder.organization_id == tenant.organization_id,
        )
    )
    if work_order is None:
        raise HTTPException(status_code=404, detail="Work order not found")
    return work_order


@router.post(
    "",
    response_model=WorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[write_roles],
)
async def create_work_order(
    payload: WorkOrderCreate,
    session: DatabaseSession,
    tenant: Tenant,
    user: CurrentUser,
) -> WorkOrder:
    property_ = await session.scalar(
        select(Property).where(
            Property.id == payload.property_id,
            Property.organization_id == tenant.organization_id,
        )
    )
    if property_ is None:
        raise HTTPException(status_code=404, detail="Property not found")
    if payload.unit_id is not None:
        unit = await session.scalar(
            select(Unit).where(
                Unit.id == payload.unit_id,
                Unit.property_id == payload.property_id,
                Unit.organization_id == tenant.organization_id,
            )
        )
        if unit is None:
            raise HTTPException(status_code=404, detail="Unit not found in property")
    if payload.assigned_to_id is not None:
        assignee = await session.scalar(
            select(Membership).where(
                Membership.user_id == payload.assigned_to_id,
                Membership.organization_id == tenant.organization_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        if assignee is None:
            raise HTTPException(status_code=400, detail="Assignee is not an active member")

    work_order = WorkOrder(
        organization_id=tenant.organization_id,
        property_id=payload.property_id,
        unit_id=payload.unit_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        priority=payload.priority,
        status=WorkOrderStatus.OPEN,
        reported_by_id=user.id,
        assigned_to_id=payload.assigned_to_id,
        due_at=payload.due_at,
    )
    session.add(work_order)
    await session.flush()
    if payload.assigned_to_id is not None:
        create_notification(
            session,
            organization_id=tenant.organization_id,
            recipient_user_id=payload.assigned_to_id,
            category="maintenance",
            title="Work order assigned",
            body=work_order.title,
            resource_type="work_order",
            resource_id=work_order.id,
        )
    record_audit_event(
        session,
        organization_id=tenant.organization_id,
        actor_user_id=user.id,
        action="work_order.created",
        resource_type="work_order",
        resource_id=work_order.id,
    )
    await session.commit()
    return work_order


@router.get("", response_model=list[WorkOrderResponse])
async def list_work_orders(
    session: DatabaseSession,
    tenant: Tenant,
    work_order_status: Annotated[WorkOrderStatus | None, Query(alias="status")] = None,
) -> list[WorkOrder]:
    query = select(WorkOrder).where(WorkOrder.organization_id == tenant.organization_id)
    if work_order_status is not None:
        query = query.where(WorkOrder.status == work_order_status)
    result = await session.scalars(query.order_by(WorkOrder.created_at.desc()))
    return list(result.all())


@router.patch(
    "/{work_order_id}",
    response_model=WorkOrderResponse,
    dependencies=[write_roles],
)
async def update_work_order(
    work_order_id: UUID,
    payload: WorkOrderUpdate,
    session: DatabaseSession,
    tenant: Tenant,
    user: CurrentUser,
) -> WorkOrder:
    work_order = await find_work_order(session, tenant, work_order_id)
    if payload.status is not None and payload.status != work_order.status:
        try:
            transition_work_order(work_order, payload.status)
        except InvalidWorkOrderTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    if payload.priority is not None:
        work_order.priority = payload.priority
    if "assigned_to_id" in payload.model_fields_set:
        if payload.assigned_to_id is not None:
            assignee = await session.scalar(
                select(Membership).where(
                    Membership.user_id == payload.assigned_to_id,
                    Membership.organization_id == tenant.organization_id,
                    Membership.status == MembershipStatus.ACTIVE,
                )
            )
            if assignee is None:
                raise HTTPException(status_code=400, detail="Assignee is not an active member")
        work_order.assigned_to_id = payload.assigned_to_id
    if "due_at" in payload.model_fields_set:
        work_order.due_at = payload.due_at
    record_audit_event(
        session,
        organization_id=tenant.organization_id,
        actor_user_id=user.id,
        action="work_order.updated",
        resource_type="work_order",
        resource_id=work_order.id,
        details={"status": work_order.status.value},
    )
    if payload.assigned_to_id is not None and payload.assigned_to_id != user.id:
        create_notification(
            session,
            organization_id=tenant.organization_id,
            recipient_user_id=payload.assigned_to_id,
            category="maintenance",
            title="Work order assigned",
            body=work_order.title,
            resource_type="work_order",
            resource_id=work_order.id,
        )
    await session.commit()
    return work_order


@router.post(
    "/{work_order_id}/comments",
    response_model=WorkOrderCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_work_order_comment(
    work_order_id: UUID,
    payload: WorkOrderCommentCreate,
    session: DatabaseSession,
    tenant: Tenant,
    user: CurrentUser,
) -> WorkOrderComment:
    await find_work_order(session, tenant, work_order_id)
    comment = WorkOrderComment(
        organization_id=tenant.organization_id,
        work_order_id=work_order_id,
        author_user_id=user.id,
        body=payload.body.strip(),
    )
    session.add(comment)
    await session.commit()
    return comment


@router.get("/{work_order_id}/comments", response_model=list[WorkOrderCommentResponse])
async def list_work_order_comments(
    work_order_id: UUID,
    session: DatabaseSession,
    tenant: Tenant,
) -> list[WorkOrderComment]:
    await find_work_order(session, tenant, work_order_id)
    result = await session.scalars(
        select(WorkOrderComment)
        .where(
            WorkOrderComment.work_order_id == work_order_id,
            WorkOrderComment.organization_id == tenant.organization_id,
        )
        .order_by(WorkOrderComment.created_at)
    )
    return list(result.all())
