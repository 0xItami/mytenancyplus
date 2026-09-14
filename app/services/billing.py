import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import OutboxEvent
from app.models.billing import (
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    WebhookReceipt,
)
from app.models.organization import Organization


class InvalidWebhookError(ValueError):
    pass


class WebhookConflictError(ValueError):
    pass


def payload_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def process_subscription_event(
    session: AsyncSession,
    *,
    event: dict[str, Any],
    raw_payload: bytes,
) -> tuple[WebhookReceipt, bool]:
    try:
        event_id = str(event["id"])
        event_type = str(event["type"])
        data = event["data"]
        organization_id = UUID(str(data["organization_id"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidWebhookError("Malformed billing event") from exc

    digest = payload_digest(raw_payload)
    existing = await session.scalar(
        select(WebhookReceipt).where(WebhookReceipt.provider_event_id == event_id)
    )
    if existing is not None:
        if existing.payload_hash != digest:
            raise WebhookConflictError("An event ID was reused with a different payload")
        return existing, True

    organization = await session.get(Organization, organization_id)
    if organization is None:
        raise InvalidWebhookError("Unknown organization")

    receipt = WebhookReceipt(
        provider_event_id=event_id,
        event_type=event_type,
        organization_id=organization_id,
        payload_hash=digest,
        processing_status="processing",
        event_metadata={"provider": str(event.get("provider", "demo"))},
    )
    session.add(receipt)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        concurrent_receipt = await session.scalar(
            select(WebhookReceipt).where(WebhookReceipt.provider_event_id == event_id)
        )
        if concurrent_receipt is None:
            raise
        if concurrent_receipt.payload_hash != digest:
            raise WebhookConflictError("An event ID was reused with a different payload") from None
        return concurrent_receipt, True

    if event_type in {"subscription.created", "subscription.updated", "subscription.cancelled"}:
        try:
            plan = SubscriptionPlan(str(data["plan"]))
            status = SubscriptionStatus(str(data["status"]))
        except (KeyError, ValueError) as exc:
            raise InvalidWebhookError("Invalid subscription state") from exc

        if session.bind is not None and session.bind.dialect.name == "postgresql":
            await session.execute(
                text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
                {"organization_id": str(organization_id)},
            )
        subscription = await session.scalar(
            select(Subscription).where(Subscription.organization_id == organization_id)
        )
        if subscription is None:
            subscription = Subscription(
                organization_id=organization_id,
                provider=str(event.get("provider", "demo")),
                plan=plan,
                status=status,
            )
            session.add(subscription)
        subscription.plan = plan
        subscription.status = status
        subscription.provider_customer_id = data.get("provider_customer_id")
        subscription.provider_subscription_id = data.get("provider_subscription_id")
        subscription.cancel_at_period_end = bool(data.get("cancel_at_period_end", False))
        period_end = data.get("current_period_end")
        try:
            subscription.current_period_end = (
                datetime.fromisoformat(str(period_end).replace("Z", "+00:00"))
                if period_end
                else None
            )
        except ValueError as exc:
            raise InvalidWebhookError("Invalid subscription period end") from exc
        session.add(
            OutboxEvent(
                organization_id=organization_id,
                topic="billing.subscription_changed",
                payload={
                    "event_id": event_id,
                    "plan": plan.value,
                    "status": status.value,
                },
            )
        )

    receipt.processing_status = "processed"
    receipt.processed_at = datetime.now(UTC)
    await session.commit()
    return receipt, False
