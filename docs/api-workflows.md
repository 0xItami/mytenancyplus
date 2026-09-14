# API workflows

All examples assume the API is available at `http://localhost:8000/api/v1`. Use the interactive
OpenAPI documentation for complete schemas and response examples.

## Account and organization

1. Register with `POST /auth/register`.
2. Exchange email and password at `POST /auth/token` using OAuth form fields `username` and
   `password`.
3. Create a workspace with `POST /organizations`.
4. Send its ID in `X-Organization-ID` for tenant-scoped endpoints.
5. Refresh with `POST /auth/refresh`; replace both stored tokens after every success.
6. Revoke the refresh session with `POST /auth/logout`.

## Team invitation

1. An owner or admin sends `POST /organizations/invitations` with an email and role.
2. The API commits the invitation and an outbox delivery event together.
3. The worker reconstructs a signed, expiring credential for the delivery consumer.
4. The invited user registers or signs in with the same email.
5. They send the credential to `POST /organizations/invitations/accept`.
6. The API verifies signature, expiry, email binding, digest, and single use before creating or
   reactivating membership.

Local and test environments return `delivery_token` directly. Production responses omit it; a
mail delivery consumer must deliver the worker event.

## Property and lease

1. Create a property at `POST /properties`.
2. Add rentable inventory at `POST /properties/units`.
3. Add a tenant profile at `POST /tenants`.
4. Create the tenancy at `POST /leases`.

An active lease is rejected when its date range intersects another active lease for the same unit.

## Maintenance

Create a work order at `POST /work-orders`. Supported state transitions are:

```text
open -> triaged -> in_progress -> resolved -> closed
  |         |            |           |
  +---------+------------+----------> cancelled
                              resolved -> in_progress
```

Assignments create recipient notifications. Comments are available under
`/work-orders/{id}/comments`. Invalid state jumps return `409 Conflict`.

## Documents

Send a multipart request to `POST /documents` with `file`, `resource_type`, and `resource_id`.
Use `GET /documents/{id}/content` for authenticated download and `DELETE /documents/{id}` for
audited metadata-and-content deletion.

## Billing webhook contract

The demo provider endpoint is `POST /billing/webhooks/demo`. Compute a lowercase HMAC-SHA256 hex
digest over the exact request body using `MTP_BILLING_WEBHOOK_SECRET`, then send it in
`X-Webhook-Signature`.

```json
{
  "id": "evt_001",
  "type": "subscription.updated",
  "provider": "demo",
  "data": {
    "organization_id": "00000000-0000-0000-0000-000000000000",
    "plan": "growth",
    "status": "active",
    "provider_customer_id": "customer_001",
    "provider_subscription_id": "subscription_001",
    "current_period_end": "2026-10-14T12:00:00Z",
    "cancel_at_period_end": false
  }
}
```

An identical replay is accepted without repeating its mutation. Reusing an event ID with different
content returns `409 Conflict`.
