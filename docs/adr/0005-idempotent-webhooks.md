# ADR 0005: Verify and deduplicate billing webhooks

## Status

Accepted

## Decision

Verify billing callbacks with an HMAC over the exact request bytes. Persist each provider event ID
with its payload digest before applying the subscription projection. Accept an identical replay and
reject reuse of an event ID with different content.

## Consequences

Provider retries cannot duplicate state transitions or outbox messages. A unique database index
also handles concurrent deliveries. Provider adapters must supply stable event IDs, and the receipt
table needs a retention policy in a hosted deployment.
