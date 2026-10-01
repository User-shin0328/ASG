"""Exercise concurrent execution of one approved action in the isolated Compose project."""
from __future__ import annotations

import concurrent.futures
import json
import os
import time
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000")
ALICE = os.environ["AGENT_ALICE_TOKEN"]
REVIEWER = os.environ["REVIEWER_TOKEN"]


def call(method: str, path: str, token: str, body: dict | None = None, key: str | None = None) -> tuple[int, dict]:
    raw = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    req = urllib.request.Request(BASE + path, data=raw, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def main() -> None:
    task = "task-alice-001"
    created = call("POST", "/v1/actions", ALICE,
        {"task_id": task, "tool": "save_summary", "arguments": {"document_id": "report-alice-001", "content": "Isolated concurrency verification; fictional summary."}}, "b04-save-" + uuid.uuid4().hex)
    if created[0] != 200:
        raise SystemExit("Could not create the isolated fictional summary")
    artifact = created[1].get("result", {}).get("result", {}).get("artifact_id")
    if not artifact:
        raise SystemExit("The Gateway response did not include the summary artifact ID")
    pending = call("POST", "/v1/actions", ALICE,
        {"task_id": task, "tool": "send_report", "arguments": {"artifact_id": artifact, "destination_id": "internal-review-outbox"}}, "b04-submit-" + uuid.uuid4().hex)
    approval = pending[1].get("approval_id")
    action_id = pending[1].get("action_id")
    if pending[0] != 202 or pending[1].get("state") != "PENDING_APPROVAL" or not approval or not action_id:
        raise SystemExit("The submission did not enter the approval queue")
    decided = call("POST", f"/v1/approvals/{approval}/decision", REVIEWER, {"decision": "approve"})
    if decided[0] != 200 or decided[1].get("state") != "APPROVED":
        raise SystemExit("The reviewer could not approve the isolated action")

    def execute(_: int) -> tuple[int, dict, float]:
        started = time.perf_counter()
        status, result = call("POST", f"/v1/actions/{action_id}/execute", ALICE)
        return status, result, (time.perf_counter() - started) * 1000

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(execute, range(20)))
    elapsed = time.perf_counter() - start
    states = {}
    receipts = set()
    statuses = {}
    latencies = []
    for status, result, latency in results:
        statuses[str(status)] = statuses.get(str(status), 0) + 1
        state = result.get("state", result.get("error", "UNKNOWN"))
        states[state] = states.get(state, 0) + 1
        receipt = result.get("result", {}).get("receipt_id")
        if receipt:
            receipts.add(receipt)
        latencies.append(latency)
    ordered = sorted(latencies)
    output = {"execution_requests": len(results), "concurrency": 10, "elapsed_seconds": round(elapsed, 3),
              "statuses": statuses, "states": states, "unique_receipt_ids": len(receipts),
              "p50_ms": round(ordered[9], 3), "p95_ms": round(ordered[18], 3), "max_ms": round(max(ordered), 3)}
    print(json.dumps(output, indent=2))
    if statuses != {"200": 20} or states != {"SUCCEEDED": 20} or len(receipts) != 1:
        raise SystemExit("Concurrent approvals did not resolve to exactly one receipt")


if __name__ == "__main__":
    main()
