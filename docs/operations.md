# Operations runbook

## Health and telemetry

- `/api/v1/health/live` proves the process can serve HTTP.
- `/api/v1/health/ready` proves the process can reach its database dependency.
- `/metrics` exposes request totals and duration histograms for Prometheus.
- Every response includes `X-Request-ID`; structured logs carry the same identifier.

A production platform should alert on readiness failures, elevated 5xx rates, latency percentiles,
outbox age, worker failures, and database connection saturation.

## Migrations

Apply migrations once per release before replacing application instances:

```bash
alembic upgrade head
```

CI verifies that ORM metadata has no unapplied schema changes. Test downgrades in a disposable
environment; production rollback should normally use a forward corrective migration after new
schema data has been written.

## Worker recovery

Outbox rows remain unpublished while the worker is unavailable. Restarting workers resumes the
oldest entries first. Multiple workers may run safely because batches use row locks with
`SKIP LOCKED`.

Watch the count and age of rows where `published_at IS NULL`. A growing backlog indicates Redis
unavailability, insufficient worker capacity, or poison events.

## Secrets

Generate independent high-entropy values for `MTP_JWT_SECRET` and
`MTP_BILLING_WEBHOOK_SECRET`. Store them in a managed secret store and never commit `.env`.
Production configuration rejects short secrets.

## Documents

Compose persists content in the `document_data` volume. Production should replace the local
adapter with encrypted private object storage, short-lived download authorization, malware
scanning, lifecycle policies, and tested backups. Database and object backups need a consistent
recovery point.

## Rate limiting

Authentication and webhooks use a Redis fixed window keyed by a digest of the client address. The
limiter fails open during Redis interruption to preserve availability and writes a warning log.
An edge gateway should add volumetric protection in production.

## Release checklist

1. Run backend lint, formatting, strict typing, and tests.
2. Run frontend strict typing and the production build.
3. Build both container images.
4. Review migrations and backup compatibility.
5. Deploy migrations, API, workers, then the web image.
6. Verify readiness, authentication, organization context, worker backlog, logs, and metrics.
