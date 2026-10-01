"""Run the plan's authenticated, no-side-effect Gateway inspection workload."""
from __future__ import annotations

import concurrent.futures
import json
import os
import time
import urllib.request

URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000") + "/v1/inputs/inspect"
TOKEN = os.environ["AGENT_ALICE_TOKEN"]
RATE = 20
DURATION_SECONDS = 60
CONCURRENCY = 10
RUNS = 3
WARMUP_SECONDS = 10


def request(index: int) -> tuple[float, int | str]:
    body = json.dumps({"source": "perf:local-controlled", "text": f"Summarize the assigned fictional document; sample {index}."}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
            status: int | str = response.status
    except Exception as exc:  # The report counts failures instead of hiding them.
        status = type(exc).__name__ + ":" + str(exc)[:120]
    return (time.perf_counter() - started) * 1000, status


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))], 3)


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as file:
            return file.read().strip()
    except OSError:
        return ""


def run_burst(pool: concurrent.futures.ThreadPoolExecutor, count: int, duration: int, serial: int) -> dict:
    start = time.perf_counter()
    futures = []
    for index in range(count):
        deadline = start + index / RATE
        delay = deadline - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        futures.append(pool.submit(request, serial * 1000000 + index))
    latencies: list[float] = []
    errors: dict[str, int] = {}
    for future in futures:
        latency, status = future.result()
        latencies.append(latency)
        if status != 200:
            key = str(status)
            errors[key] = errors.get(key, 0) + 1
    elapsed = time.perf_counter() - start
    return {"offered_requests": count, "offered_rps": RATE, "completed_requests": len(latencies),
            "duration_seconds": duration, "elapsed_seconds": round(elapsed, 3),
            "actual_rps": round(len(latencies) / elapsed, 3), "errors": errors,
            "p50_ms": percentile(latencies, 0.50), "p95_ms": percentile(latencies, 0.95),
            "max_ms": round(max(latencies), 3)}


def main() -> None:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        for run in range(1, RUNS + 1):
            warmup = run_burst(pool, RATE * WARMUP_SECONDS, WARMUP_SECONDS, -run)
            cpu_before = read_text("/sys/fs/cgroup/cpu.stat")
            run_result = run_burst(pool, RATE * DURATION_SECONDS, DURATION_SECONDS, run)
            cpu_after = read_text("/sys/fs/cgroup/cpu.stat")
            memory_peak = read_text("/sys/fs/cgroup/memory.peak")
            try:
                before = dict(line.split() for line in cpu_before.splitlines())
                after = dict(line.split() for line in cpu_after.splitlines())
                cpu_seconds = round((int(after["usage_usec"]) - int(before["usage_usec"])) / 1_000_000, 3)
            except (KeyError, ValueError):
                cpu_seconds = None
            run_result.update({"run": run, "warmup_requests": warmup["completed_requests"],
                               "warmup_duration_seconds": WARMUP_SECONDS, "cgroup_cpu_seconds": cpu_seconds,
                               "cgroup_peak_memory_bytes": int(memory_peak) if memory_peak.isdigit() else None})
            results.append(run_result)
    print(json.dumps({"route": "POST /v1/inputs/inspect", "concurrency": CONCURRENCY,
                      "runs": results, "resource_measurement": "Gateway container cgroup CPU delta and peak memory"}, indent=2))


if __name__ == "__main__":
    main()
