"""Probe request-body and tool-argument size limits without creating actions."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000")
TOKEN = os.environ["AGENT_ALICE_TOKEN"]


def post(payload: dict, key: str) -> tuple[int, str | None]:
    raw = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + "/v1/actions", data=raw,
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json", "Idempotency-Key": key}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
            return response.status, None
    except urllib.error.HTTPError as exc:
        try:
            error = json.loads(exc.read()).get("error")
        except Exception:
            error = None
        return exc.code, error


def main() -> None:
    oversized_body = post({"padding": "x" * 24000}, "boundary-body-" + uuid.uuid4().hex)
    oversized_argument = post({"task_id": "task-alice-001", "tool": "save_summary",
        "arguments": {"document_id": "report-alice-001", "content": "x" * 8001}}, "boundary-argument-" + uuid.uuid4().hex)
    result = {"request_bytes_over_limit": {"http_status": oversized_body[0], "error": oversized_body[1], "expected": 413},
              "tool_argument_chars_over_limit": {"http_status": oversized_argument[0], "error": oversized_argument[1], "expected": 422}}
    print(json.dumps(result, indent=2))
    if oversized_body[0] != 413 or oversized_argument[0] != 422:
        raise SystemExit("A request-size boundary returned an unexpected result")


if __name__ == "__main__":
    main()
