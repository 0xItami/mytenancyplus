import hashlib
import hmac
import json
from typing import Any

from httpx import AsyncClient

PASSWORD = "a-secure-test-password"


async def register_and_login(client: AsyncClient, email: str) -> dict[str, str]:
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Operations Tester", "password": PASSWORD},
    )
    assert register.status_code == 201, register.text
    login = await client.post("/api/v1/auth/token", data={"username": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {key: str(value) for key, value in login.json().items()}


def headers(access_token: str, organization_id: str | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {access_token}"}
    if organization_id is not None:
        result["X-Organization-ID"] = organization_id
    return result


async def create_organization(client: AsyncClient, token: str) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/organizations",
        headers=headers(token),
        json={"name": "Harbour Property Operations"},
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


async def create_property(client: AsyncClient, token: str, organization_id: str) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/properties",
        headers=headers(token, organization_id),
        json={
            "name": "Marina Court",
            "address_line": "8 Harbour Road",
            "city": "Lagos",
            "country_code": "NG",
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


async def invite_manager(
    client: AsyncClient,
    *,
    owner_token: str,
    manager_token: str,
    organization_id: str,
) -> str:
    invitation = await client.post(
        "/api/v1/organizations/invitations",
        headers=headers(owner_token, organization_id),
        json={"email": "manager-ops@example.com", "role": "manager"},
    )
    assert invitation.status_code == 202, invitation.text
    delivery_token = invitation.json()["delivery_token"]
    assert delivery_token
    acceptance = await client.post(
        "/api/v1/organizations/invitations/accept",
        headers=headers(manager_token),
        json={"token": delivery_token},
    )
    assert acceptance.status_code == 200, acceptance.text
    return str(acceptance.json()["user_id"])


async def test_refresh_tokens_rotate_and_revoke_reused_families(client: AsyncClient) -> None:
    tokens = await register_and_login(client, "sessions@example.com")
    first_refresh = tokens["refresh_token"]
    rotation = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert rotation.status_code == 200, rotation.text
    second_refresh = str(rotation.json()["refresh_token"])
    assert second_refresh != first_refresh

    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert reuse.status_code == 401
    assert "reuse" in reuse.json()["detail"].lower()

    revoked_family = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": second_refresh}
    )
    assert revoked_family.status_code == 401


async def test_invitation_maintenance_notifications_dashboard_and_audit(
    client: AsyncClient,
) -> None:
    owner = await register_and_login(client, "owner-ops@example.com")
    manager = await register_and_login(client, "manager-ops@example.com")
    organization = await create_organization(client, owner["access_token"])
    organization_id = str(organization["id"])
    property_ = await create_property(client, owner["access_token"], organization_id)
    manager_id = await invite_manager(
        client,
        owner_token=owner["access_token"],
        manager_token=manager["access_token"],
        organization_id=organization_id,
    )
    members = await client.get(
        "/api/v1/organizations/members",
        headers=headers(owner["access_token"], organization_id),
    )
    assert members.status_code == 200
    assert {member["email"] for member in members.json()} == {
        "owner-ops@example.com",
        "manager-ops@example.com",
    }

    owner_headers = headers(owner["access_token"], organization_id)
    work_order_response = await client.post(
        "/api/v1/work-orders",
        headers=owner_headers,
        json={
            "property_id": property_["id"],
            "title": "Repair lobby water leak",
            "description": "Water is collecting beside the lobby service riser.",
            "priority": "urgent",
            "assigned_to_id": manager_id,
        },
    )
    assert work_order_response.status_code == 201, work_order_response.text
    work_order = work_order_response.json()
    assert work_order["status"] == "open"

    invalid_transition = await client.patch(
        f"/api/v1/work-orders/{work_order['id']}",
        headers=owner_headers,
        json={"status": "closed"},
    )
    assert invalid_transition.status_code == 409

    for target_status in ("triaged", "in_progress", "resolved", "closed"):
        transition = await client.patch(
            f"/api/v1/work-orders/{work_order['id']}",
            headers=owner_headers,
            json={"status": target_status},
        )
        assert transition.status_code == 200, transition.text
        assert transition.json()["status"] == target_status

    comment = await client.post(
        f"/api/v1/work-orders/{work_order['id']}/comments",
        headers=headers(manager["access_token"], organization_id),
        json={"body": "Leak isolated and damaged coupling replaced."},
    )
    assert comment.status_code == 201, comment.text

    notification_list = await client.get(
        "/api/v1/notifications?unread_only=true",
        headers=headers(manager["access_token"], organization_id),
    )
    assert notification_list.status_code == 200
    assert len(notification_list.json()) == 1
    notification_id = notification_list.json()[0]["id"]
    marked = await client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=headers(manager["access_token"], organization_id),
    )
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    dashboard = await client.get("/api/v1/dashboard/summary", headers=owner_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json() == {
        "properties": 1,
        "units": 0,
        "active_leases": 0,
        "open_work_orders": 0,
        "unread_notifications": 0,
        "subscription_plan": "starter",
        "subscription_status": "trialing",
    }

    audit = await client.get("/api/v1/audit-logs", headers=owner_headers)
    assert audit.status_code == 200
    assert {event["action"] for event in audit.json()} >= {
        "property.created",
        "work_order.created",
        "work_order.updated",
    }
    forbidden_audit = await client.get(
        "/api/v1/audit-logs",
        headers=headers(manager["access_token"], organization_id),
    )
    assert forbidden_audit.status_code == 403


async def test_document_lifecycle(client: AsyncClient) -> None:
    owner = await register_and_login(client, "documents@example.com")
    organization = await create_organization(client, owner["access_token"])
    organization_id = str(organization["id"])
    property_ = await create_property(client, owner["access_token"], organization_id)
    owner_headers = headers(owner["access_token"], organization_id)
    content = b"Signed lease evidence for the portfolio test."

    upload = await client.post(
        "/api/v1/documents",
        headers=owner_headers,
        data={"resource_type": "property", "resource_id": property_["id"]},
        files={"file": ("lease evidence.txt", content, "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()
    assert document["size_bytes"] == len(content)
    assert document["checksum_sha256"] == hashlib.sha256(content).hexdigest()

    listing = await client.get(
        f"/api/v1/documents?resource_id={property_['id']}", headers=owner_headers
    )
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [document["id"]]

    download = await client.get(
        f"/api/v1/documents/{document['id']}/content", headers=owner_headers
    )
    assert download.status_code == 200
    assert download.content == content

    deletion = await client.delete(f"/api/v1/documents/{document['id']}", headers=owner_headers)
    assert deletion.status_code == 204
    unavailable = await client.get(
        f"/api/v1/documents/{document['id']}/content", headers=owner_headers
    )
    assert unavailable.status_code == 404


async def test_billing_webhooks_are_verified_and_idempotent(client: AsyncClient) -> None:
    owner = await register_and_login(client, "billing@example.com")
    organization = await create_organization(client, owner["access_token"])
    organization_id = str(organization["id"])
    event: dict[str, Any] = {
        "id": "evt_portfolio_001",
        "type": "subscription.created",
        "provider": "demo",
        "data": {
            "organization_id": organization_id,
            "plan": "growth",
            "status": "active",
            "provider_customer_id": "customer_001",
            "provider_subscription_id": "subscription_001",
            "current_period_end": "2026-10-14T12:00:00Z",
        },
    }
    payload = json.dumps(event, separators=(",", ":")).encode()
    signature = hmac.new(b"test-billing-webhook-secret", payload, hashlib.sha256).hexdigest()

    invalid = await client.post(
        "/api/v1/billing/webhooks/demo",
        content=payload,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": "invalid"},
    )
    assert invalid.status_code == 401

    webhook_headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
    }
    first = await client.post(
        "/api/v1/billing/webhooks/demo", content=payload, headers=webhook_headers
    )
    duplicate = await client.post(
        "/api/v1/billing/webhooks/demo", content=payload, headers=webhook_headers
    )
    assert first.status_code == 202, first.text
    assert first.json()["duplicate"] is False
    assert duplicate.status_code == 202, duplicate.text
    assert duplicate.json()["duplicate"] is True

    subscription = await client.get(
        "/api/v1/billing/subscription",
        headers=headers(owner["access_token"], organization_id),
    )
    assert subscription.status_code == 200, subscription.text
    assert subscription.json()["plan"] == "growth"
    assert subscription.json()["status"] == "active"

    changed_event = {**event, "data": {**event["data"], "plan": "scale"}}
    changed_payload = json.dumps(changed_event, separators=(",", ":")).encode()
    changed_signature = hmac.new(
        b"test-billing-webhook-secret", changed_payload, hashlib.sha256
    ).hexdigest()
    conflict = await client.post(
        "/api/v1/billing/webhooks/demo",
        content=changed_payload,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": changed_signature,
        },
    )
    assert conflict.status_code == 409
