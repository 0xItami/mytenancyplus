# MyTenancyPlus

MyTenancyPlus is a production-oriented, multi-tenant property operations platform. It brings
property inventory, leases, maintenance, evidence, team access, and operational oversight into one
accountable workspace.

This repository focuses on the engineering concerns that appear after a prototype: tenant
isolation, authorization, session security, explicit workflow state, transactional consistency,
auditability, idempotent integrations, background delivery, observability, and repeatable
operations.

## Product capabilities

- Responsive web workspace for portfolio overview, properties, work orders, documents,
  notifications, and organization governance.
- Argon2 password hashing, short-lived JWT access tokens, rotating opaque refresh tokens, and
  token-family revocation when reuse is detected.
- Organizations, invitation acceptance, and owner/admin/manager/viewer authorization.
- Defense-in-depth tenant isolation through explicit query scoping and PostgreSQL row-level
  security.
- Properties, rentable units, tenant profiles, and overlap-safe lease creation.
- Maintenance work orders with guarded state transitions, priority, assignment, comments, and
  recipient notifications.
- Streamed document upload, SHA-256 integrity metadata, size enforcement, safe storage keys,
  authenticated download, and audited deletion.
- Signed billing webhooks, event-ID idempotency, payload-conflict detection, and subscription
  projections.
- Immutable audit records and a transactional outbox dispatched by independently scalable ARQ
  workers.
- Structured logs, correlation IDs, health probes, Prometheus metrics, Redis-backed rate limits,
  database migrations, Docker images, and CI quality gates.

## System shape

```text
React admin console
        |
        v
FastAPI application ---- Redis (rate limits, queues, event stream)
        |
        +---- PostgreSQL (source of truth + row-level security)
        |           |
        |           +---- audit log
        |           +---- transactional outbox
        |                            |
        v                            v
Prometheus metrics              ARQ worker
```

The code is a modular monolith by design. It preserves one transactional boundary while keeping
domain modules explicit enough to extract only when measured load, ownership, or deployment
pressure makes the cost worthwhile.

## Technology

- **API:** Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic
- **Data and delivery:** PostgreSQL 17, Redis, ARQ, transactional outbox
- **Web:** React 19, TypeScript, Vite, Nginx
- **Operations:** Docker Compose, Prometheus metrics, structlog, GitHub Actions
- **Quality:** pytest, pytest-cov, Ruff, strict mypy, TypeScript strict mode

## Run the complete platform

Docker Desktop or another Docker Engine must be running.

```bash
cp .env.example .env
docker compose up --build
```

| Surface | URL |
| --- | --- |
| Web workspace | `http://localhost:3002` |
| OpenAPI documentation | `http://localhost:8000/docs` |
| API readiness | `http://localhost:8000/api/v1/health/ready` |
| Prometheus metrics | `http://localhost:8000/metrics` |

The Compose stack applies migrations before the API starts. PostgreSQL, Redis, and uploaded
documents use separate persistent volumes.

## Local development

```bash
python -m venv .venv
.venv/Scripts/activate           # Windows
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd web
npm install
npm run dev
```

Copy `.env.example` to `.env` and use `localhost` for dependency hosts when running the API outside
Compose. The web development server runs on port `3002`.

## Request context

Authentication returns access and refresh tokens. After creating or joining an organization,
tenant-scoped requests must include:

```http
Authorization: Bearer <access-token>
X-Organization-ID: <organization-id>
```

The application verifies active membership before setting PostgreSQL's transaction-local tenant
context. Row-level security then enforces the same boundary at the database layer.

See [API workflows](docs/api-workflows.md) for complete registration, invitation, maintenance,
document, and billing examples.

## Quality gates

```bash
ruff check .
ruff format --check .
mypy app tests
pytest --cov=app --cov-fail-under=70
cd web && npm run typecheck && npm run build
```

CI repeats those checks and builds both production containers. Tests cover service rules,
authentication, tenant boundaries, property and lease workflows, refresh-token reuse, invitation
acceptance, maintenance transitions, notifications, documents, billing signatures and idempotency,
dashboard aggregation, and audit authorization.

## Engineering documentation

- [Architecture overview](docs/architecture.md)
- [API workflows](docs/api-workflows.md)
- [Operations runbook](docs/operations.md)
- [Architecture decision records](docs/adr)
- [Security policy](SECURITY.md)
- [Contribution guide](CONTRIBUTING.md)

## Milestone status

Version `0.2.0` completes the portfolio operations milestone: the secure tenancy core, operational
domains, integration safeguards, background delivery, administration interface, container stack,
tests, CI, and engineering documentation are implemented together.

This repository is an engineering portfolio project and is not offered as a hosted property
management service.
