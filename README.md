# MyTenancyPlus

MyTenancyPlus is a production-oriented, multi-tenant property operations platform. It is
designed to demonstrate the backend concerns that appear after a CRUD prototype: tenant
isolation, authorization, transactional consistency, auditability, background delivery,
observability, migrations, and repeatable operations.

## What it does

- Registers and authenticates users with Argon2 and short-lived JWT access tokens.
- Creates organizations and role-based memberships.
- Isolates every organization using application checks and PostgreSQL row-level security.
- Manages properties, rentable units, tenant profiles, and leases.
- Prevents overlapping active leases for a unit.
- Records auditable administrative actions.
- Commits domain events through a transactional outbox and dispatches them with ARQ workers.
- Exposes structured logs, request correlation IDs, health probes, and Prometheus metrics.

## Technology

Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL 17, Alembic, Redis, ARQ, Pydantic,
Prometheus, Docker Compose, Ruff, mypy, pytest, and GitHub Actions.

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

The API is available at `http://localhost:8000`, interactive documentation at
`http://localhost:8000/docs`, and metrics at `http://localhost:8000/metrics`.

## First request flow

1. `POST /api/v1/auth/register`
2. `POST /api/v1/auth/token` using the email as the OAuth `username`
3. `POST /api/v1/organizations`
4. Add the returned organization ID as `X-Organization-ID` to tenant-scoped requests.
5. Create properties, units, tenants, and leases through the documented API.

## Quality checks

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy app tests
pytest --cov=app
```

## Architecture

Read [the architecture overview](docs/architecture.md) and the
[architecture decision records](docs/adr). The project intentionally begins as a modular
monolith: service extraction should follow measured pressure, not fashion.

## Status and roadmap

The current milestone establishes the secure platform core. Planned milestones add invitation
acceptance, refresh-token rotation, billing subscriptions and webhook idempotency, maintenance
work orders, documents, notifications, rate limiting, end-to-end PostgreSQL isolation tests,
and a web administration experience.

This repository is an engineering portfolio project and is not offered as a hosted property
management service.

