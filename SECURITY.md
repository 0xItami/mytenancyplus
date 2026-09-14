# Security policy

Please report vulnerabilities privately through GitHub's **Report a vulnerability** feature.
Do not open a public issue containing exploit details or tenant data.

## Security boundaries

- Organization membership and PostgreSQL row-level security protect tenant data.
- Passwords use Argon2 and are never logged.
- Access tokens are short-lived; refresh credentials rotate and only hashed secrets are stored.
- Reuse of an already rotated refresh token revokes its full token family.
- Billing callbacks require an HMAC signature and an idempotent provider event ID.
- Uploaded documents have bounded size, sanitized storage keys, authenticated access, and content
  checksums.
- Public authentication and webhook routes use Redis-backed request limits.
- Runtime secrets are supplied through the environment and production rejects unsafe defaults.
- Audit entries capture sensitive administrative changes without storing credentials.

## Deployment expectations

- Terminate TLS at a trusted proxy and add edge-level denial-of-service protection.
- Use a dedicated least-privilege PostgreSQL application role; do not run the API as a superuser or
  table owner because those roles can bypass row-level security.
- Store documents in private encrypted object storage with malware scanning in hosted deployments.
- Rotate signing secrets through a coordinated rollout and monitor refresh-token reuse alerts.
- Do not expose Redis or PostgreSQL publicly.

This repository is a portfolio system and has not undergone an external security audit.
