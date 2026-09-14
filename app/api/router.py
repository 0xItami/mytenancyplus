from fastapi import APIRouter

from app.api.routes import (
    audit,
    auth,
    billing,
    dashboard,
    documents,
    health,
    leases,
    maintenance,
    notifications,
    organizations,
    properties,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(leases.router, tags=["tenancies"])
api_router.include_router(maintenance.router, prefix="/work-orders", tags=["maintenance"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(audit.router, prefix="/audit-logs", tags=["audit"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
