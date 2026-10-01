from __future__ import annotations

import os
import secrets
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
KEYS = ("AGENT_ALICE_TOKEN", "AGENT_BOB_TOKEN", "REVIEWER_TOKEN", "TOOL_SERVICE_TOKEN")
DATABASE_SECRETS = ("postgres_password", "gateway_db_password")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-dir", type=Path, default=ROOT, help="Directory for ignored .env and secrets files")
    args = parser.parse_args()
    config_root = args.target_dir.resolve()
    config_root.mkdir(parents=True, exist_ok=True)
    env_path = config_root / ".env"
    existing = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    defaults = {"TOOL_DATABASE_PATH": "/data/tool.sqlite3", "TOOL_URL": "http://tool-sandbox:8001"}
    changed = not env_path.exists()
    for obsolete in ("DATABASE_PATH", "GATEWAY_PORT"):
        if obsolete in existing:
            existing.pop(obsolete)
            changed = True
    for key in KEYS:
        if not existing.get(key) or len(existing[key]) < 32 or "replace-with" in existing[key]:
            existing[key] = secrets.token_urlsafe(36)
            changed = True
    for key, value in defaults.items():
        if key not in existing:
            existing[key] = value
            changed = True
    secret_dir = config_root / "secrets"
    secret_dir.mkdir(exist_ok=True)
    for name in DATABASE_SECRETS:
        secret_path = secret_dir / f"{name}.txt"
        if not secret_path.exists() or len(secret_path.read_text(encoding="utf-8").strip()) < 32:
            secret_path.write_bytes((secrets.token_urlsafe(48) + "\n").encode("ascii"))
        elif name == "gateway_db_password" and b"\r" in secret_path.read_bytes():
            secret_path.write_bytes((secret_path.read_text(encoding="utf-8").strip() + "\n").encode("ascii"))
    if changed or not ENV.exists():
        env_path.write_text("# Local demo credentials. Never commit this file.\n" + "".join(f"{k}={existing[k]}\n" for k in [*KEYS, *defaults]), encoding="utf-8")
    print(f"Local configuration is ready under {config_root}. Existing valid credentials were preserved.")
    print("Demo credential names: AGENT_ALICE_TOKEN, AGENT_BOB_TOKEN, REVIEWER_TOKEN")
    print("Credential values are stored in the ignored .env and secrets files; values are not displayed.")


if __name__ == "__main__":
    main()
