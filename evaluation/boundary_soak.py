"""Sustain oversized Gateway rejections while sampling container memory."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return round(ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))], 4)


def memory_bytes(docker: str, container: str) -> int | None:
    try:
        raw = subprocess.check_output([docker, "stats", "--no-stream", "--format", "{{.MemUsage}}", container], text=True, timeout=10).strip()
        value = raw.split("/", 1)[0].strip().lower()
        factors = {"b": 1, "kib": 1024, "mib": 1024 ** 2, "gib": 1024 ** 3}
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(b|kib|mib|gib)", value)
        if not match:
            return None
        return int(float(match.group(1)) * factors[match.group(2)])
    except Exception:
        return None


def post(base: str, token: str, payload: dict, timeout: int = 5) -> tuple[int, float, str | None]:
    raw = json.dumps(payload).encode()
    request = urllib.request.Request(base.rstrip("/") + "/v1/actions", data=raw,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "Idempotency-Key": "soak-" + uuid.uuid4().hex}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            return response.status, time.perf_counter() - started, None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read()
            error = json.loads(body).get("error") if body else None
        except Exception:
            error = None
        return exc.code, time.perf_counter() - started, error
    except Exception as exc:
        return 0, time.perf_counter() - started, type(exc).__name__


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway", default=os.environ.get("GATEWAY_URL", "http://127.0.0.1:18501"))
    parser.add_argument("--token", default=os.environ.get("AGENT_ALICE_TOKEN"))
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--container", default="ai-agent-security-gateway-gateway-1")
    parser.add_argument("--duration", type=int, default=180)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--sample-seconds", type=float, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.token or not 30 <= args.duration <= 600 or not 0.1 <= args.interval <= 2:
        raise SystemExit("token, duration 30..600s, and interval 0.1..2s are required")
    started = datetime.now(timezone.utc).isoformat()
    deadline = time.monotonic() + args.duration
    latencies: dict[str, list[float]] = {"request_too_large": [], "argument_too_large": []}
    statuses: dict[str, dict[str, int]] = {"request_too_large": {}, "argument_too_large": {}}
    samples = []
    cycle = 0
    next_sample = 0.0
    while time.monotonic() < deadline:
        kind = "request_too_large" if cycle % 2 == 0 else "argument_too_large"
        if kind == "request_too_large":
            payload = {"padding": "x" * 24000}
            expected = 413
        else:
            payload = {"task_id": "task-alice-001", "tool": "save_summary",
                       "arguments": {"document_id": "report-alice-001", "content": "x" * 8001}}
            expected = 422
        status, elapsed, error = post(args.gateway, args.token, payload)
        latencies[kind].append(elapsed)
        key = f"{status}:{error or 'no_error'}"
        statuses[kind][key] = statuses[kind].get(key, 0) + 1
        cycle += 1
        now = time.monotonic()
        if status != expected:
            statuses[kind][f"unexpected_expected_{expected}"] = statuses[kind].get(f"unexpected_expected_{expected}", 0) + 1
        if now >= next_sample:
            samples.append({"elapsed_seconds": round(args.duration - max(0, deadline - now), 2),
                            "gateway_memory_bytes": memory_bytes(args.docker, args.container)})
            next_sample = now + args.sample_seconds
        delay = args.interval - (time.monotonic() - now)
        if delay > 0:
            time.sleep(min(delay, max(0, deadline - time.monotonic())))
    metrics = {kind: {"requests": len(latencies[kind]), "statuses": statuses[kind],
                      "latency_seconds": {"p50": percentile(latencies[kind], .5),
                                          "p95": percentile(latencies[kind], .95),
                                          "max": round(max(latencies[kind], default=0), 4)}}
               for kind in latencies}
    memory_values = [sample["gateway_memory_bytes"] for sample in samples if sample["gateway_memory_bytes"] is not None]
    result = {"started_at": started, "duration_seconds": args.duration, "request_interval_seconds": args.interval,
              "total_requests": cycle, "checks": metrics,
              "gateway_memory_samples": samples,
              "gateway_memory_min_bytes": min(memory_values) if memory_values else None,
              "gateway_memory_max_bytes": max(memory_values) if memory_values else None,
              "gateway_memory_sample_range_bytes": (max(memory_values) - min(memory_values)) if memory_values else None,
              "gateway_memory_peak_above_first_sample_bytes": (max(memory_values) - memory_values[0]) if memory_values else None,
              "gateway_memory_end_delta_bytes": (memory_values[-1] - memory_values[0]) if memory_values else None,
              "side_effects_expected": 0, "source": "synthetic oversized input only"}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "total_requests": cycle,
                      "gateway_memory_peak_above_first_sample_bytes": result["gateway_memory_peak_above_first_sample_bytes"],
                      "all_expected_statuses": all("unexpected_expected_" not in key for group in statuses.values() for key in group)}, indent=2))
    if any("unexpected_expected_" in key for group in statuses.values() for key in group) or cycle < 100 or not memory_values:
        raise SystemExit("Boundary soak failed a status, request-count, or memory-sampling requirement")


if __name__ == "__main__":
    main()
