import json
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select

from app.api.dependencies import DatabaseSession, Tenant
from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limit
from app.models.billing import Subscription
from app.schemas.billing import SubscriptionResponse, WebhookResponse
from app.services.billing import (
    InvalidWebhookError,
    WebhookConflictError,
    process_subscription_event,
    verify_webhook_signature,
)

router = APIRouter()


@router.get("/subscription", response_model=SubscriptionResponse | None)
async def read_subscription(session: DatabaseSession, tenant: Tenant) -> Subscription | None:
    return cast(
        Subscription | None,
        await session.scalar(
            select(Subscription).where(Subscription.organization_id == tenant.organization_id)
        ),
    )


@router.post(
    "/webhooks/demo",
    response_model=WebhookResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[rate_limit("billing-webhook", requests=120)],
)
async def receive_billing_webhook(
    request: Request,
    session: DatabaseSession,
    signature: Annotated[str, Header(alias="X-Webhook-Signature")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WebhookResponse:
    raw_payload = await request.body()
    if not verify_webhook_signature(raw_payload, signature, settings.billing_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        event = json.loads(raw_payload)
        if not isinstance(event, dict):
            raise InvalidWebhookError("Billing event must be an object")
        receipt, duplicate = await process_subscription_event(
            session,
            event=event,
            raw_payload=raw_payload,
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    except InvalidWebhookError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WebhookConflictError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return WebhookResponse(duplicate=duplicate, event_id=receipt.provider_event_id)
