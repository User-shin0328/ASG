"""Run the B01 assigned-document read workload against the isolated Gateway stack."""
from __future__ import annotations

import concurrent.futures
import json
import os
import time
import urllib.error
import urllib.request

URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000") + "/v1/actions"
TOKEN = os.environ["AGENT_ALICE_TOKEN"]
RATE, DURATION, CONCURRENCY, RUNS = 20, 60, 10, 3


def request(index: int) -> tuple[float, int | str, str]:
    body = json.dumps({"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-alice-001"}}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Authorization": "Bearer " + TOKEN,
        "Content-Type": "application/json", "Idempotency-Key": f"b01-read-load-{index}"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read())
            status = response.status
    except urllib.error.HTTPError as exc:
        try:
            result = json.loads(exc.read() or b"{}")
        except Exception:
            result = {}
        status = exc.code
    except Exception as exc:
        result, status = {}, type(exc).__name__ + ":" + str(exc)[:120]
    return (time.perf_counter() - started) * 1000, status, str(result.get("state", result.get("error", "UNKNOWN")))


def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def burst(pool: concurrent.futures.ThreadPoolExecutor, count: int, serial: int) -> dict:
    start = time.perf_counter()
    futures = []
    for i in range(count):
        delay = start + i / RATE - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        futures.append(pool.submit(request, serial * 1000000 + i))
    latencies, statuses, states = [], {}, {}
    for future in futures:
        latency, status, state = future.result()
        latencies.append(latency)
        statuses[str(status)] = statuses.get(str(status), 0) + 1
        states[state] = states.get(state, 0) + 1
    elapsed = time.perf_counter() - start
    ordered = sorted(latencies)
    return {"offered": count, "completed": len(latencies), "actual_rps": round(len(latencies) / elapsed, 3),
            "elapsed_seconds": round(elapsed, 3), "statuses": statuses, "states": states,
            "p50_ms": round(ordered[int((len(ordered)-1)*.50)], 3),
            "p95_ms": round(ordered[int((len(ordered)-1)*.95)], 3), "max_ms": round(max(ordered), 3)}


def main() -> None:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        for run in range(1, RUNS + 1):
            warmup = burst(pool, RATE * 10, -run)
            cpu_before = read("/sys/fs/cgroup/cpu.stat")
            result = burst(pool, RATE * DURATION, run)
            cpu_after = read("/sys/fs/cgroup/cpu.stat")
            try:
                before = dict(line.split() for line in cpu_before.splitlines())
                after = dict(line.split() for line in cpu_after.splitlines())
                cpu_seconds = round((int(after["usage_usec"]) - int(before["usage_usec"])) / 1_000_000, 3)
            except (KeyError, ValueError):
                cpu_seconds = None
            result.update({"run": run, "warmup_requests": warmup["completed"], "warmup_duration_seconds": 10,
                           "cgroup_cpu_seconds": cpu_seconds, "cgroup_peak_memory_bytes": int(read("/sys/fs/cgroup/memory.peak") or 0)})
            results.append(result)
    print(json.dumps({"route": "POST /v1/actions (assigned read_document)", "offered_rps": RATE,
                      "duration_seconds": DURATION, "concurrency": CONCURRENCY, "runs": results}, indent=2))
    if any(run["statuses"] != {"200": RATE * DURATION} or run["states"] != {"SUCCEEDED": RATE * DURATION} for run in results):
        raise SystemExit("One or more assigned document reads did not complete successfully")


if __name__ == "__main__":
    main()
