"""Evaluate the unchanged local detectors on a pinned external agentic test split.

Rows are fetched in memory from the Hugging Face dataset viewer. Only aggregate
metrics and hashes are retained; raw rows and per-case decisions are not saved.
This is a text-classification diagnostic, not an end-to-end agent outcome test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from demo_agent.input_classifier import SYSTEM_PROMPT, classify_untrusted_text
from evaluation.metrics import summarize
from gateway.app.core import INSPECTION_SCANNER_VERSION, scan_untrusted_text


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "3nesdeniz/agentic-prompt-injection-5k"
REVISION = "e658d94"
SPLIT = "test"
EXPECTED_ROWS = 545
PAGE_SIZE = 100
ROWS_API = "https://datasets-server.huggingface.co/rows"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def fetch_rows() -> list[dict]:
    rows: list[dict] = []
    expected_total: int | None = None
    for offset in range(0, EXPECTED_ROWS, PAGE_SIZE):
        query = urllib.parse.urlencode({
            "dataset": DATASET_ID,
            "config": "default",
            "split": SPLIT,
            "offset": offset,
            "length": PAGE_SIZE,
            "revision": REVISION,
        })
        request = urllib.request.Request(
            f"{ROWS_API}?{query}",
            headers={"User-Agent": "AI-Agent-Security-Gateway-evaluation/1.0"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            page = json.loads(response.read())
        total = page.get("num_rows_total")
        if expected_total is None:
            expected_total = total
        if total != expected_total or total != EXPECTED_ROWS:
            raise SystemExit("Pinned external test split row count changed")
        for wrapped in page.get("rows", []):
            row = wrapped.get("row", {})
            text = row.get("text")
            label = row.get("label")
            row_id = row.get("id")
            if not isinstance(text, str) or label not in (0, 1) or not isinstance(row_id, int):
                raise SystemExit("External test split did not match its expected schema")
            rows.append({
                "id": row_id,
                "text": text,
                "label": "malicious" if label == 1 else "normal",
                "family": str(row.get("attack_family", "unknown")),
                "technique": str(row.get("technique", "unknown")),
            })
        print(f"loaded external rows: {len(rows)}/{EXPECTED_ROWS}", flush=True)
    if len(rows) != EXPECTED_ROWS or len({row["id"] for row in rows}) != EXPECTED_ROWS:
        raise SystemExit("External test split was incomplete or had duplicate IDs")
    if len({row["text"].casefold().strip() for row in rows}) != EXPECTED_ROWS:
        raise SystemExit("External test split contains duplicate normalized text")
    return rows


def dataset_digest(rows: list[dict]) -> str:
    manifest = [
        {
            "id": row["id"],
            "text_sha256": sha256_bytes(row["text"].encode("utf-8")),
            "label": row["label"],
            "family": row["family"],
            "technique": row["technique"],
        }
        for row in sorted(rows, key=lambda item: item["id"])
    ]
    encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def local_text_hashes() -> set[str]:
    paths = [ROOT / "evaluation/datasets/dev.jsonl", *sorted((ROOT / "evaluation/datasets").glob("heldout-v*.jsonl"))]
    hashes: set[str] = set()
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                text = json.loads(line).get("text")
                if isinstance(text, str):
                    hashes.add(sha256_bytes(text.casefold().strip().encode("utf-8")))
    return hashes


def evaluate_rules(rows: list[dict]) -> dict:
    decisions = [{
        "label": row["label"],
        "family": row["family"],
        "detected": bool(scan_untrusted_text(row["text"])),
    } for row in rows]
    result = summarize(decisions)
    result["scanner_version"] = INSPECTION_SCANNER_VERSION
    return result


def evaluate_semantic(rows: list[dict], base: str, model: str, timeout: int) -> dict:
    decisions = []
    latencies = []
    errors = 0
    for index, row in enumerate(rows, 1):
        label, elapsed, error = classify_untrusted_text(base, model, row["text"], timeout)
        latencies.append(elapsed)
        errors += error is not None
        decisions.append({
            "label": row["label"],
            "family": row["family"],
            "detected": label == "malicious",
        })
        if index % 50 == 0:
            print(f"semantic progress: {index}/{len(rows)}", flush=True)
    ordered = sorted(latencies)
    result = summarize(decisions)
    result["inference_errors"] = errors
    result["latency_seconds"] = {
        "p50": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.5))],
        "p95": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.95))],
        "max": max(ordered),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("all", "rules", "semantic"), default="all")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    parser.add_argument("--ollama", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--output", type=Path, help="Optional aggregate-only JSON output; an existing file is never overwritten")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        raise SystemExit("timeout must be between 1 and 120 seconds")
    if args.output and args.output.exists():
        raise SystemExit("Output already exists; choose a new result path")

    rows = fetch_rows()
    local_hashes = local_text_hashes()
    overlap = sum(
        sha256_bytes(row["text"].casefold().strip().encode("utf-8")) in local_hashes
        for row in rows
    )
    labels = Counter(row["label"] for row in rows)
    families = Counter(row["family"] for row in rows)
    metrics = {}
    if args.mode in {"all", "rules"}:
        metrics["rules"] = evaluate_rules(rows)

    model_manifest = None
    if args.mode in {"all", "semantic"}:
        base = args.ollama.rstrip("/")
        with urllib.request.urlopen(base + "/api/version", timeout=5) as response:
            version = json.loads(response.read())
        with urllib.request.urlopen(base + "/api/tags", timeout=5) as response:
            available = json.loads(response.read()).get("models", [])
        model_info = next((entry for entry in available if entry.get("name") == args.model), None)
        if model_info is None:
            raise SystemExit(f"Requested local model is not installed: {args.model}")
        model_manifest = {
            "name": args.model,
            "digest": model_info.get("digest"),
            "ollama_version": version.get("version"),
            "system_prompt_sha256": sha256_bytes(SYSTEM_PROMPT.encode("utf-8")),
        }
        metrics["semantic"] = evaluate_semantic(rows, base, args.model, args.timeout)

    result = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "id": DATASET_ID,
            "source_url": "https://huggingface.co/datasets/3nesdeniz/agentic-prompt-injection-5k",
            "revision": REVISION,
            "split": SPLIT,
            "rows": len(rows),
            "labels": dict(sorted(labels.items())),
            "families": dict(sorted(families.items())),
            "normalized_row_manifest_sha256": dataset_digest(rows),
            "exact_text_overlap_with_local_sets": overlap,
            "license": "CC-BY-4.0",
            "raw_rows_written": False,
            "per_case_decisions_written": False,
        },
        "environment": {"python": platform.python_version(), "model": model_manifest},
        "metrics": metrics,
        "scope_note": "External text-classification diagnostic on a scenario-isolated test split; this does not evaluate agent action outcomes or Gateway authorization.",
    }
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
