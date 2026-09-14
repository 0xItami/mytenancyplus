from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


def create_notification(
    session: AsyncSession,
    *,
    organization_id: UUID,
    recipient_user_id: UUID,
    category: str,
    title: str,
    body: str,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
) -> Notification:
    notification = Notification(
        organization_id=organization_id,
        recipient_user_id=recipient_user_id,
        category=category,
        title=title,
        body=body,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    session.add(notification)
    return notification
