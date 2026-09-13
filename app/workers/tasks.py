import json
from datetime import UTC, datetime
from typing import Any

import structlog
from arq.connections import ArqRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.base import OutboxEvent

logger = structlog.get_logger()


async def publish_outbox_events(context: dict[Any, Any], *_args: Any, **_kwargs: Any) -> None:
    """Publish committed domain events in bounded, independently claimable batches."""

    session_factory: async_sessionmaker[AsyncSession] = context["session_factory"]
    redis: ArqRedis = context["redis"]
    async with session_factory() as session:
        result = await session.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at)
            .limit(100)
            .with_for_update(skip_locked=True)
        )
        events = list(result.all())
        for event in events:
            await redis.xadd(
                "mytenancyplus:domain-events",
                {
                    "event_id": str(event.id),
                    "topic": event.topic,
                    "organization_id": str(event.organization_id),
                    "payload": json.dumps(event.payload, separators=(",", ":")),
                },
            )
            await logger.ainfo(
                "domain_event_published",
                event_id=str(event.id),
                topic=event.topic,
                organization_id=str(event.organization_id),
            )
            event.published_at = datetime.now(UTC)
            event.last_error = None
        await session.commit()
