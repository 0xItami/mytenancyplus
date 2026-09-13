# Architecture

MyTenancyPlus begins as a modular monolith. Authentication, organization management,
property inventory, tenancy, auditing, and asynchronous delivery share one deployment and
one transactional database while keeping explicit module boundaries.

```text
Client
  |
  v
FastAPI API ---- Redis (queue, cache, rate-limit foundation)
  |
  +---- PostgreSQL (source of truth and row-level security)
  |          |
  |          +---- transactional outbox
  |                         |
  v                         v
Prometheus              ARQ worker
metrics                 event delivery
```

## Request isolation

1. The bearer token identifies a user.
2. `X-Organization-ID` selects the active organization.
3. Membership is verified before any tenant-owned query executes.
4. Every repository query includes `organization_id` explicitly.
5. PostgreSQL row-level security provides a second isolation boundary.

This defense-in-depth design makes a missing application filter less likely to become a
cross-tenant data disclosure.

## Consistency

Business state, audit entries, and outbox events are written in one transaction. The worker
locks pending outbox rows with `SKIP LOCKED`, allowing several workers to run concurrently.
Production consumers must remain idempotent because distributed delivery is at-least-once.

## Scaling boundary

The API and worker already scale independently. A module should become a separate service
only after measured load, reliability ownership, or deployment cadence justifies the added
network and operational complexity.

