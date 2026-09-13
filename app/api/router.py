from fastapi import APIRouter

from app.api.routes import auth, health, leases, organizations, properties

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(leases.router, tags=["tenancies"])
