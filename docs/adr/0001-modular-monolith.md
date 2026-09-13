# ADR 0001: Start with a modular monolith

- Status: Accepted
- Date: 2026-09-13

## Context

The product needs strong domain boundaries but does not yet have independent teams or
measured scaling requirements.

## Decision

Deploy one FastAPI application with separated API, service, persistence, and worker modules.
PostgreSQL remains the system of record; workers scale separately.

## Consequences

Local development, transactions, refactoring, and debugging stay simple. Modules may be
extracted later, but extraction will require explicit APIs and operational ownership.

