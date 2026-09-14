# ADR 0006: Keep document content behind a storage adapter

## Status

Accepted

## Decision

Persist document metadata in PostgreSQL and stream content through a filesystem adapter. Keys
include organization and document identifiers; filenames are sanitized, upload size is bounded,
and a SHA-256 checksum is recorded.

## Consequences

The local stack remains self-contained without placing binary data in transactional tables. The
adapter is narrow enough to replace with object storage. Database and content deletion cannot be
fully atomic, so failed database writes remove staged content and operators must reconcile rare
storage failures.
