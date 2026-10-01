# Database migrations

The current reference implementation initializes its SQLite schema in `gateway/app/core.py` and `tool_sandbox/app.py`. The source plan requires PostgreSQL for Gateway state. No PostgreSQL migration is claimed here; create and verify the PostgreSQL schema and migration runner before declaring v0.1 complete.
