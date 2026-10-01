from __future__ import annotations

import hashlib
import os
import secrets
import sys
import tempfile
import time
from pathlib import Path

import psycopg
from psycopg.conninfo import make_conninfo


ROOT_ENV = Path(os.environ.get("DEMO_ENV_FILE", "/workspace/.env"))
KEYS = {
    "alice": ("AGENT_ALICE_TOKEN", "agent-alice"),
    "bob": ("AGENT_BOB_TOKEN", "agent-bob"),
    "reviewer": ("REVIEWER_TOKEN", "reviewer-demo"),
}


def parse_env(path: Path) -> tuple[list[str], dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    values = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return lines, values


def admin_connection():
    password_file = Path(os.environ["DATABASE_ADMIN_PASSWORD_FILE"])
    password = password_file.read_text(encoding="utf-8").strip()
    if len(password) < 32:
        raise RuntimeError("PostgreSQL administrator secret is missing or too short")
    dsn = make_conninfo(
        host=os.environ.get("DATABASE_HOST", "postgres"),
        port=os.environ.get("DATABASE_PORT", "5432"),
        dbname=os.environ.get("DATABASE_NAME", "gateway"),
        user=os.environ.get("DATABASE_ADMIN_USER", "postgres"),
        password=password,
        connect_timeout=5,
        application_name="ai-agent-security-token-rotation",
    )
    return psycopg.connect(dsn)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in KEYS:
        raise SystemExit("Usage: rotate_demo_token.py alice|bob|reviewer")
    env_key, principal = KEYS[sys.argv[1]]
    original_content = ROOT_ENV.read_bytes()
    lines, values = parse_env(ROOT_ENV)
    old_token = values.get(env_key, "")
    if len(old_token) < 32:
        raise RuntimeError(f"{env_key} is missing or too short in the local .env file")
    new_token = secrets.token_urlsafe(48)
    replaced, found = [], False
    for line in lines:
        if line.partition("=")[0].strip() == env_key and "=" in line:
            replaced.append(f"{env_key}={new_token}")
            found = True
        else:
            replaced.append(line)
    if not found:
        replaced.append(f"{env_key}={new_token}")

    # Stage the new file first. The old credential is not logged or printed.
    fd, temp_name = tempfile.mkstemp(prefix=".env.rotate.", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as staged:
            staged.write("\n".join(replaced) + "\n")
        old_hash = hashlib.sha256(old_token.encode("utf-8")).hexdigest()
        with admin_connection() as connection:
            with connection.transaction():
                cursor = connection.execute(
                    "UPDATE token_registry SET revoked=%s WHERE token_hash=%s AND principal=%s AND revoked IS NULL",
                    (time.time(), old_hash, principal),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("The current token was not found as active; .env was not changed")
            try:
                with ROOT_ENV.open("wb") as env_file, open(temp_name, "rb") as staged:
                    env_file.write(staged.read())
                    env_file.flush()
                    os.fsync(env_file.fileno())
            except OSError:
                with connection.transaction():
                    connection.execute("UPDATE token_registry SET revoked=NULL WHERE token_hash=%s AND principal=%s", (old_hash, principal))
                ROOT_ENV.write_bytes(original_content)
                raise
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print(f"Rotated {principal}; token value was not displayed. Restart the Gateway to activate the new credential.")


if __name__ == "__main__":
    main()
