"""Stress one Gateway idempotency key across multiple live processes."""
from __future__ import annotations

import concurrent.futures
import json
import os
import statistics
import time
import urllib.error
import urllib.request
import uuid


def post_action(base_url: str, token: str, key: str, body: dict) -> tuple[int, dict, float]:
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/actions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "Idempotency-Key": key},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read()), time.perf_counter() - started
    except urllib.error.HTTPError as error:
        payload = error.read()
        try:
            result = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            result = {}
        return error.code, result, time.perf_counter() - started
    except urllib.error.URLError:
        return 0, {}, time.perf_counter() - started


def main() -> None:
    targets = [item.rstrip("/") for item in os.environ.get("GATEWAY_STRESS_URLS", "").split(",") if item.strip()]
    if len(targets) < 2 or len(set(targets)) != len(targets):
        raise SystemExit("Set GATEWAY_STRESS_URLS to at least two distinct Gateway base URLs")
    token = os.environ.get("AGENT_ALICE_TOKEN", "")
    if len(token) < 32:
        raise SystemExit("AGENT_ALICE_TOKEN is missing or too short")
    try:
        count = int(os.environ.get("GATEWAY_STRESS_REQUESTS", "100"))
        workers = int(os.environ.get("GATEWAY_STRESS_WORKERS", "32"))
    except ValueError as error:
        raise SystemExit("Request and worker counts must be integers") from error
    if not 2 <= count <= 1000 or not 2 <= workers <= count:
        raise SystemExit("Use 2-1000 requests and 2-request-count workers")

    body = {
        "task_id": "task-alice-001",
        "tool": "save_summary",
        "arguments": {
            "document_id": "report-alice-001",
            "content": "Isolated cross-process idempotency stress; fictional data only.",
        },
    }
    key = "multiprocess-stress-" + uuid.uuid4().hex
    requests = [(targets[index % len(targets)], token, key, body) for index in range(count)]
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        responses = list(pool.map(lambda values: post_action(*values), requests))
    elapsed = time.perf_counter() - started

    statuses = {str(code): sum(item[0] == code for item in responses) for code in sorted({item[0] for item in responses})}
    action_ids = {item[1].get("action_id") for item in responses}
    receipt_ids = [
        item[1]["result"].get("receipt_id")
        if isinstance(item[1].get("result"), dict)
        else None
        for item in responses
    ]
    receipts = {receipt for receipt in receipt_ids if receipt}
    latencies_ms = sorted(item[2] * 1000 for item in responses)
    summary = {
        "requests": count,
        "workers": workers,
        "gateway_processes": len(targets),
        "statuses": statuses,
        "unique_action_ids": len(action_ids - {None}),
        "missing_action_ids": sum(item[1].get("action_id") is None for item in responses),
        "unique_receipt_ids": len(receipts),
        "missing_receipt_ids": sum(not receipt for receipt in receipt_ids),
        "elapsed_seconds": round(elapsed, 3),
        "p50_ms": round(statistics.median(latencies_ms), 3),
        "p95_ms": round(latencies_ms[min(len(latencies_ms) - 1, int(len(latencies_ms) * 0.95))], 3),
        "max_ms": round(max(latencies_ms), 3),
    }
    print(json.dumps(summary, indent=2))
    if statuses != {"200": count} or summary["unique_action_ids"] != 1 or summary["unique_receipt_ids"] != 1 or summary["missing_receipt_ids"]:
        raise SystemExit("Cross-process retries did not converge to one successful action and receipt")


if __name__ == "__main__":
    main()
