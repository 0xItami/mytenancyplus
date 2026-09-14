from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import DatabaseSession, Tenant, require_roles
from app.models.audit import AuditLog
from app.models.organization import MembershipRole
from app.schemas.audit import AuditLogResponse

router = APIRouter()
read_roles = require_roles(MembershipRole.OWNER, MembershipRole.ADMIN)


@router.get("", response_model=list[AuditLogResponse], dependencies=[read_roles])
async def list_audit_logs(
    session: DatabaseSession,
    tenant: Tenant,
    limit: int = Query(default=100, ge=1, le=250),
) -> list[AuditLog]:
    result = await session.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == tenant.organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return list(result.all())
