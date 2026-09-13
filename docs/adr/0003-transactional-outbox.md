# ADR 0003: Use a transactional outbox

- Status: Accepted
- Date: 2026-09-13

## Context

Writing business data and publishing a queue message as separate operations creates a
dual-write failure: either operation can succeed alone.

## Decision

Store domain events in PostgreSQL in the same transaction as business changes. Workers claim
and publish committed events asynchronously.

## Consequences

Requests do not depend on broker availability. Delivery is eventually consistent and
at-least-once, so consumers must use event IDs for idempotency.

