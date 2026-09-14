import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from arq.connections import ArqRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.security import create_invitation_token
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
            delivery_payload = dict(event.payload)
            if event.topic == "organization.member_invited":
                delivery_payload["invitation_token"] = create_invitation_token(
                    invitation_id=UUID(str(event.payload["invitation_id"])),
                    organization_id=UUID(str(event.payload["organization_id"])),
                    token_id=str(event.payload["token_id"]),
                    email=str(event.payload["email"]),
                    expires_at=datetime.fromisoformat(str(event.payload["expires_at"])),
                    settings=get_settings(),
                )
            await redis.xadd(
                "mytenancyplus:domain-events",
                {
                    "event_id": str(event.id),
                    "topic": event.topic,
                    "organization_id": str(event.organization_id),
                    "payload": json.dumps(delivery_payload, separators=(",", ":")),
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
