from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg.conninfo import make_conninfo


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"


def _admin_dsn() -> str:
    password_file = Path(os.environ["DATABASE_ADMIN_PASSWORD_FILE"])
    password = password_file.read_text(encoding="utf-8").strip()
    if len(password) < 32:
        raise RuntimeError("PostgreSQL administrator secret is missing or too short")
    return make_conninfo(
        host=os.environ.get("DATABASE_HOST", "postgres"),
        port=os.environ.get("DATABASE_PORT", "5432"),
        dbname=os.environ.get("DATABASE_NAME", "gateway"),
        user=os.environ.get("DATABASE_ADMIN_USER", "postgres"),
        password=password,
        connect_timeout=5,
        application_name="ai-agent-security-migrate",
    )


def main() -> None:
    migration_files = sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))
    if not migration_files:
        raise RuntimeError("No PostgreSQL migrations found")

    with psycopg.connect(_admin_dsn()) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        for migration in migration_files:
            with connection.transaction():
                already_applied = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = %s", (migration.name,)
                ).fetchone()
                if already_applied:
                    continue
                connection.execute(migration.read_text(encoding="utf-8"))
                connection.execute("INSERT INTO schema_migrations(version) VALUES (%s)", (migration.name,))
            print(f"Applied PostgreSQL migration {migration.name}")
        print("PostgreSQL schema is current")


if __name__ == "__main__":
    main()
