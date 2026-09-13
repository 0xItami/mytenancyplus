from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.dependencies import DatabaseSession

router = APIRouter()


@router.get("/health/live", summary="Process liveness")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", summary="Dependency readiness")
async def readiness(session: DatabaseSession) -> Response:
    await session.execute(text("SELECT 1"))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
