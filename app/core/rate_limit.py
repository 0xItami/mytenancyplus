import hashlib
import time
from collections.abc import Callable
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.params import Depends as DependsParam
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings
from app.core.redis import RedisClient

logger = structlog.get_logger()


def rate_limit(scope: str, *, requests: int | None = None) -> DependsParam:
    """Return a fixed-window Redis rate-limit dependency for a route group."""

    async def enforce(
        request: Request,
        redis: RedisClient,
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> None:
        if settings.environment == "test":
            return
        limit = requests or settings.rate_limit_requests
        window = settings.rate_limit_window_seconds
        client = request.client.host if request.client else "unknown"
        subject = hashlib.sha256(client.encode()).hexdigest()[:20]
        bucket = int(time.time() // window)
        key = f"mytenancyplus:rate:{scope}:{subject}:{bucket}"
        try:
            async with redis.pipeline(transaction=True) as pipeline:
                pipeline.incr(key)
                pipeline.expire(key, window + 1)
                count, _ = await pipeline.execute()
        except RedisError as exc:
            await logger.awarning("rate_limiter_unavailable", scope=scope, error=str(exc))
            return
        if int(count) > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Request limit exceeded",
                headers={"Retry-After": str(window)},
            )

    dependency: Callable[..., object] = enforce
    return DependsParam(dependency=dependency)
