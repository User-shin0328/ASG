"""Exercise a sustained cross-tenant denial burst without invoking tools."""
from __future__ import annotations

import concurrent.futures
import json
import os
import time
import urllib.error
import urllib.request

URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000") + "/v1/actions"
TOKEN = os.environ["AGENT_ALICE_TOKEN"]
RATE, DURATION, CONCURRENCY = 20, 60, 10


def request(index: int) -> tuple[float, int | str]:
    body = json.dumps({"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-bob-001"}}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json", "Idempotency-Key": f"b02-denial-load-{index}"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
            status: int | str = response.status
    except urllib.error.HTTPError as exc:
        exc.read()
        status = exc.code
    except Exception as exc:
        status = type(exc).__name__ + ":" + str(exc)[:120]
    return (time.perf_counter() - started) * 1000, status


def burst(pool: concurrent.futures.ThreadPoolExecutor, count: int, serial: int) -> dict:
    start = time.perf_counter()
    futures = []
    for index in range(count):
        delay = start + index / RATE - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        futures.append(pool.submit(request, serial * 1000000 + index))
    latencies, counts = [], {}
    for future in futures:
        latency, status = future.result()
        latencies.append(latency)
        counts[str(status)] = counts.get(str(status), 0) + 1
    elapsed = time.perf_counter() - start
    ordered = sorted(latencies)
    return {"offered": count, "completed": len(latencies), "actual_rps": round(len(latencies) / elapsed, 3),
            "elapsed_seconds": round(elapsed, 3), "status_counts": counts,
            "p50_ms": round(ordered[int((len(ordered)-1)*.50)], 3),
            "p95_ms": round(ordered[int((len(ordered)-1)*.95)], 3), "max_ms": round(max(ordered), 3)}


def main() -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        warmup = burst(pool, RATE * 10, -1)
        measured = burst(pool, RATE * DURATION, 1)
    result = {"route": "POST /v1/actions", "scenario": "cross-tenant read denied before tool dispatch",
              "offered_rps": RATE, "duration_seconds": DURATION, "concurrency": CONCURRENCY,
              "warmup_seconds": 10, "warmup_status_counts": warmup["status_counts"], **measured}
    if measured["status_counts"] != {"403": RATE * DURATION}:
        raise SystemExit("Expected every measured request to be a policy denial (HTTP 403)")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
