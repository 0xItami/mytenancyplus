from typing import Annotated, cast

from fastapi import Depends
from redis.asyncio import Redis

from app.core.config import get_settings

redis_client = Redis.from_url(
    get_settings().redis_url,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def get_redis() -> Redis:
    return cast(Redis, redis_client)


RedisClient = Annotated[Redis, Depends(get_redis)]
