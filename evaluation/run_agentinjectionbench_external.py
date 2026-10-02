"""Attack-only diagnostic against the pinned AgentInjectionBench seed corpus.

The source contains no benign rows, so this runner reports recall only and is
not an acceptance test. Raw rows and per-case decisions stay in memory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import demo_agent.input_classifier as input_classifier
from demo_agent.input_classifier import classify_untrusted_text
from evaluation.evaluate_agentic5k_classifier import load_model
from evaluation.run_agentic5k_external import sha256_bytes
from evaluation.train_agentic5k_classifier import features
from gateway.app.core import INSPECTION_SCANNER_VERSION, scan_untrusted_text


DATASET_ID = "sincpp/AgentInjectionBench"
REVISION = "6041b9e757b834c2c60b3c046d18de2daf0f5e27"
URL = f"https://huggingface.co/datasets/{DATASET_ID}/resolve/{REVISION}/data/agent_injection_bench.jsonl"
FILE_SHA256 = "749e7cb3d346b157def7d712332aa890c7e852d7f26193f0c1d67c33fc1fc216"
EXPECTED_ROWS = 120


def load_rows() -> tuple[list[dict], str]:
    request = urllib.request.Request(URL, headers={"User-Agent": "AI-Agent-Security-Gateway-evaluation/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    source_hash = hashlib.sha256(raw).hexdigest()
    if source_hash != FILE_SHA256:
        raise SystemExit("Pinned AgentInjectionBench file SHA-256 mismatch")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(rows) != EXPECTED_ROWS or any(row.get("ground_truth") != "unsafe" for row in rows):
        raise SystemExit("Pinned AgentInjectionBench source shape changed")
    if any(not isinstance(row.get("conversation"), list) for row in rows):
        raise SystemExit("Unexpected conversation schema")
    projected = []
    for row in rows:
        tool_texts = [turn.get("content", "") for turn in row["conversation"]
                      if turn.get("role") == "tool_result" and isinstance(turn.get("content"), str)]
        if not tool_texts:
            raise SystemExit("Expected tool-result text was missing")
        projected.append({
            "id": row.get("id"),
            "surface": row.get("injection_surface", "unknown"),
            "category": row.get("attack_category", "unknown"),
            "text": "\n\n[Next tool result]\n\n".join(tool_texts),
        })
    return projected, source_hash


def recall_summary(hits: int, rows: list[dict]) -> dict:
    by_category = Counter(row["category"] for row in rows)
    return {
        "cases": len(rows),
        "detected": hits,
        "missed": len(rows) - hits,
        "recall": hits / len(rows) if rows else None,
        "categories": dict(sorted(by_category.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-file", type=Path, required=True, help="Frozen local n-gram candidate for attack-recall diagnostic")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    parser.add_argument("--ollama", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        raise SystemExit("timeout must be between 1 and 120 seconds")
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new path")

    rows, file_hash = load_rows()
    labels = {"malicious": len(rows), "normal": 0}
    surfaces = dict(sorted(Counter(row["surface"] for row in rows).items()))

    rule_hits = sum(bool(scan_untrusted_text(row["text"])) for row in rows)
    model_data, model_hash = load_model(args.model_file)
    weights = model_data["weights"]
    local_hits = sum(
        model_data["baseline_log_odds"] + sum(weights.get(feature, 0.0) for feature in features(row["text"]))
        >= model_data["threshold"]
        for row in rows
    )

    with urllib.request.urlopen(args.ollama.rstrip("/") + "/api/version", timeout=5) as response:
        ollama_version = json.loads(response.read()).get("version")
    with urllib.request.urlopen(args.ollama.rstrip("/") + "/api/tags", timeout=5) as response:
        models = json.loads(response.read()).get("models", [])
    model_info = next((entry for entry in models if entry.get("name") == args.model), None)
    if model_info is None:
        raise SystemExit(f"Requested local model is not installed: {args.model}")
    semantic_hits = 0
    errors = 0
    latencies = []
    for index, row in enumerate(rows, 1):
        label, elapsed, error = classify_untrusted_text(args.ollama, args.model, row["text"], args.timeout)
        latencies.append(elapsed)
        errors += error is not None
        semantic_hits += label == "malicious"
        if index % 25 == 0:
            print(f"attack-only diagnostic progress: {index}/{len(rows)}", flush=True)
    ordered = sorted(latencies)

    result = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "id": DATASET_ID,
            "source_url": URL,
            "revision": REVISION,
            "license": "Apache-2.0",
            "rows": len(rows),
            "labels": labels,
            "surfaces": surfaces,
            "raw_file_sha256": file_hash,
            "raw_rows_written": False,
            "per_case_decisions_written": False,
        },
        "detectors": {
            "rules": {"scanner_version": INSPECTION_SCANNER_VERSION, **recall_summary(rule_hits, rows)},
            "local_ngram_candidate": {"model_sha256": model_hash, **recall_summary(local_hits, rows)},
            "qwen_semantic": {
                "model": args.model,
                "model_digest": model_info.get("digest"),
                "ollama_version": ollama_version,
                "system_prompt_sha256": sha256_bytes(input_classifier.SYSTEM_PROMPT.encode("utf-8")),
                **recall_summary(semantic_hits, rows),
                "inference_errors": errors,
                "latency_seconds": {
                    "p50": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.5))],
                    "p95": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.95))],
                    "max": max(ordered),
                },
            },
        },
        "scope_note": "All 120 source scenarios are labeled unsafe; this attack-only diagnostic has no benign cases and cannot estimate FPR, precision, or the plan's full acceptance targets. It evaluates concatenated tool-result text, not Gateway action authorization. The source repository describes v0.1 as 120 hand-authored seed samples.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
