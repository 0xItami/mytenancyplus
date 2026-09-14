# ADR 0004: Rotating opaque refresh sessions

## Status

Accepted

## Decision

Use short-lived signed JWTs for access and stateful opaque refresh credentials for session
continuity. Store only a hash of the refresh secret. Rotate after each use and link rotations by
family. Reuse of a revoked token revokes its entire family.

## Consequences

Access authorization remains inexpensive and horizontally scalable. Refresh sessions can be
revoked, and replay after credential theft has a bounded response. The database becomes a
dependency for refresh and logout, and clients must replace both returned tokens atomically.
