# Security policy

Please report vulnerabilities privately through GitHub's **Report a vulnerability** feature.
Do not open a public issue containing exploit details or tenant data.

## Security boundaries

- Organization membership and PostgreSQL row-level security protect tenant data.
- Passwords use Argon2 and are never logged.
- Access tokens are short-lived and secrets are supplied through the environment.
- Audit entries capture sensitive administrative changes without storing credentials.

This repository is a portfolio system and has not undergone an external security audit.

