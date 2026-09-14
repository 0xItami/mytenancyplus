# Architecture

MyTenancyPlus is a modular monolith with a separately scalable worker and web client. The shape is
intentional: the domains share transactions and operational ownership today, while packages and
interfaces keep future service boundaries visible.

## Runtime components

```text
Browser
  |
  v
React + TypeScript static application (Nginx)
  |
  v
FastAPI
  +-- authentication and rotating sessions
  +-- organizations and role policy
  +-- property and tenancy operations
  +-- maintenance state machine
  +-- documents, notifications, and billing webhook adapter
  +-- dashboard projections
  |
  +---- PostgreSQL (domain state, RLS, audit log, outbox)
  +---- Redis (rate limits, ARQ queue, domain event stream)
  +---- document storage adapter
  +---- Prometheus metrics and structured logs

ARQ worker
  +---- claims committed outbox rows with SKIP LOCKED
  +---- publishes delivery-safe events to Redis
```

## Module boundaries

- `app/api` translates HTTP into application calls and enforces request-level policy.
- `app/models` defines persistence state and tenant ownership.
- `app/schemas` owns input validation and public response contracts.
- `app/services` contains business rules independent of transport.
- `app/workers` owns asynchronous delivery behavior.
- `app/core` holds configuration, security, logging, Redis, and rate limiting.
- `web/src/lib` is the browser-side transport boundary; pages do not construct authorization
  headers directly.

Routes may orchestrate several services, but business invariants live in named service functions.

## Tenant request lifecycle

1. A bearer access token identifies the user.
2. `X-Organization-ID` selects the active organization.
3. An active membership is verified before tenant-owned work begins.
4. PostgreSQL receives `app.current_organization_id` as transaction-local configuration.
5. Every application query also includes `organization_id` explicitly.
6. Row-level security applies the same predicate to reads and writes.

The duplicate checks are deliberate defense in depth: a missing query predicate does not silently
become a cross-tenant disclosure on PostgreSQL.

## Session lifecycle

Access tokens are stateless and short-lived. Refresh tokens combine a database session ID with a
high-entropy opaque secret; only its digest is stored. Refreshing rotates the token in the same
family and revokes the previous record. Presenting a rotated token again revokes the entire family.

## Consistency and delivery

Business state, audit entries, and outbox events are committed in the same database transaction.
The worker claims bounded batches with `FOR UPDATE SKIP LOCKED`, publishes them, and marks them
complete. Delivery is at least once, so consumers must use the event ID as an idempotency key.

Invitation credentials are reconstructed for delivery by the worker rather than persisted as
usable bearer secrets. Signed billing callbacks are deduplicated by provider event ID and payload
digest before mutating subscription projections.

## Documents

The API streams uploads in bounded chunks, calculates a checksum, and writes to an
organization/document-prefixed storage key. PostgreSQL stores metadata, not binary content.
`app/services/storage.py` is the adapter seam for replacing local volumes with object storage.

## Scaling decisions

The API, static web server, worker, PostgreSQL, and Redis deploy independently. A domain should
become a separate service only when materially different availability, ownership, deployment, data
boundary, or throughput requirements justify the added network and operational complexity.
