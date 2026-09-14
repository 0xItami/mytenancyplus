from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.sql.elements import ColumnElement

from app.api.dependencies import CurrentUser, DatabaseSession, Tenant
from app.models.billing import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.lease import Lease, LeaseStatus
from app.models.maintenance import WorkOrder, WorkOrderStatus
from app.models.notification import Notification
from app.models.property import Property, Unit
from app.schemas.dashboard import DashboardSummary

router = APIRouter()


async def count_for(
    session: DatabaseSession,
    model: type[Any],
    *criteria: ColumnElement[bool],
) -> int:
    result = await session.scalar(select(func.count()).select_from(model).where(*criteria))
    return result or 0


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    session: DatabaseSession, tenant: Tenant, user: CurrentUser
) -> DashboardSummary:
    organization_id = tenant.organization_id
    properties = await count_for(session, Property, Property.organization_id == organization_id)
    units = await count_for(session, Unit, Unit.organization_id == organization_id)
    active_leases = await count_for(
        session,
        Lease,
        Lease.organization_id == organization_id,
        Lease.status == LeaseStatus.ACTIVE,
    )
    open_work_orders = await count_for(
        session,
        WorkOrder,
        WorkOrder.organization_id == organization_id,
        WorkOrder.status.notin_([WorkOrderStatus.CLOSED, WorkOrderStatus.CANCELLED]),
    )
    unread_notifications = await count_for(
        session,
        Notification,
        Notification.organization_id == organization_id,
        Notification.recipient_user_id == user.id,
        Notification.read_at.is_(None),
    )
    subscription = await session.scalar(
        select(Subscription).where(Subscription.organization_id == organization_id)
    )
    return DashboardSummary(
        properties=properties,
        units=units,
        active_leases=active_leases,
        open_work_orders=open_work_orders,
        unread_notifications=unread_notifications,
        subscription_plan=(subscription.plan.value if subscription else SubscriptionPlan.STARTER),
        subscription_status=(
            subscription.status.value if subscription else SubscriptionStatus.TRIALING
        ),
    )
