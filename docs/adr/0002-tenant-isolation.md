# ADR 0002: Defense-in-depth tenant isolation

- Status: Accepted
- Date: 2026-09-13

## Decision

The active organization is supplied separately from identity, verified against membership,
included in every tenant-owned query, and enforced again using PostgreSQL row-level security.

## Consequences

Isolation is visible and testable. Background jobs must establish the same database tenant
context before reading tenant-owned rows. Operational database roles must not have `BYPASSRLS`.

