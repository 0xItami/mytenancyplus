from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


def record_audit_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    actor_user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            created_at=datetime.now(UTC),
        )
    )
