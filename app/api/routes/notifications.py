from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DatabaseSession, Tenant
from app.models.notification import Notification
from app.schemas.notification import NotificationCountResponse, NotificationResponse

router = APIRouter()


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    session: DatabaseSession,
    tenant: Tenant,
    user: CurrentUser,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[Notification]:
    query = select(Notification).where(
        Notification.organization_id == tenant.organization_id,
        Notification.recipient_user_id == user.id,
    )
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    result = await session.scalars(query.order_by(Notification.created_at.desc()).limit(limit))
    return list(result.all())


@router.get("/unread-count", response_model=NotificationCountResponse)
async def unread_notification_count(
    session: DatabaseSession, tenant: Tenant, user: CurrentUser
) -> NotificationCountResponse:
    unread = await session.scalar(
        select(func.count(Notification.id)).where(
            Notification.organization_id == tenant.organization_id,
            Notification.recipient_user_id == user.id,
            Notification.read_at.is_(None),
        )
    )
    return NotificationCountResponse(unread=unread or 0)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    session: DatabaseSession,
    tenant: Tenant,
    user: CurrentUser,
) -> Notification:
    notification = await session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == tenant.organization_id,
            Notification.recipient_user_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await session.commit()
    return notification
