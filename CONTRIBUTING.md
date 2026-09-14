# Contributing

1. Create a focused branch from `main`.
2. Install backend dependencies with `python -m pip install -e ".[dev]"` and run `npm install`
   inside `web`.
3. Keep domain rules in services and tenant checks explicit in queries.
4. Run `make check` before opening a pull request.
5. Verify both migration upgrade and downgrade paths in a disposable database.
6. Explain schema, security, delivery, or topology changes in an ADR.
7. Never commit credentials or customer data.

Commit messages should be imperative and describe the user-visible or operational outcome.
