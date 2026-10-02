"""Evaluate a validation-frozen n-gram OR local-LLM detector on held-out test."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import demo_agent.input_classifier as input_classifier
from demo_agent.input_classifier import classify_untrusted_text
from demo_agent.ngram_classifier import features, load_model
from evaluation.metrics import summarize
from evaluation.run_agentic5k_external import REVISION, dataset_digest, fetch_rows, local_text_hashes


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("validation", "test"), default="test")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    parser.add_argument("--ollama", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new result path")
    if not 1 <= args.timeout <= 120:
        raise SystemExit("timeout must be between 1 and 120 seconds")

    model, model_hash = load_model(args.model_file)
    if model.get("threshold_selection", {}).get("split") != "validation":
        raise SystemExit("Model threshold was not selected on validation")
    # Re-fetch and bind all three splits to verify no normalized-text leakage.
    train_rows = fetch_rows("train")
    validation_rows = fetch_rows("validation")
    test_rows = fetch_rows("test")
    digest = lambda row: sha256_bytes(row["text"].casefold().strip().encode("utf-8"))
    split_hashes = {name: {digest(row) for row in rows} for name, rows in
                    (("train", train_rows), ("validation", validation_rows), ("test", test_rows))}
    overlaps = {
        "train_vs_validation": len(split_hashes["train"] & split_hashes["validation"]),
        "train_vs_test": len(split_hashes["train"] & split_hashes["test"]),
        "validation_vs_test": len(split_hashes["validation"] & split_hashes["test"]),
    }
    if any(overlaps.values()):
        raise SystemExit(f"Exact normalized-text overlap across dataset splits: {overlaps}")
    if dataset_digest(train_rows) != model.get("training_manifest_sha256"):
        raise SystemExit("Training manifest changed since model freeze")
    if dataset_digest(validation_rows) != model.get("threshold_selection", {}).get("validation_manifest_sha256"):
        raise SystemExit("Validation manifest changed since threshold freeze")
    local_hashes = local_text_hashes()
    scored_rows = validation_rows if args.split == "validation" else test_rows
    local_overlap = sum(digest(row) in local_hashes for row in scored_rows)
    if local_overlap:
        raise SystemExit(f"External test overlaps local datasets: {local_overlap}")

    base = args.ollama.rstrip("/")
    with urllib.request.urlopen(base + "/api/version", timeout=5) as response:
        ollama_version = json.loads(response.read()).get("version")
    with urllib.request.urlopen(base + "/api/tags", timeout=5) as response:
        available = json.loads(response.read()).get("models", [])
    model_info = next((entry for entry in available if entry.get("name") == args.model), None)
    if model_info is None:
        raise SystemExit(f"Requested local model is not installed: {args.model}")

    weights = model["weights"]
    threshold = model["threshold"]
    baseline = model["baseline_log_odds"]
    decisions = []
    semantic_latencies = []
    feature_latencies = []
    inference_errors = 0
    for index, row in enumerate(scored_rows, 1):
        started = time.perf_counter()
        score = baseline + sum(weights.get(feature, 0.0) for feature in features(row["text"]))
        feature_latencies.append(time.perf_counter() - started)
        model_flag = score >= threshold
        semantic_label, elapsed, error = classify_untrusted_text(base, args.model, row["text"], args.timeout)
        semantic_latencies.append(elapsed)
        inference_errors += error is not None
        semantic_flag = semantic_label == "malicious"
        # Errors fail closed; recorded separately so errors cannot hide as detections.
        hybrid_flag = model_flag or semantic_flag or error is not None
        decisions.append({
            "label": row["label"],
            "family": row["family"],
            "model_detected": model_flag,
            "semantic_detected": semantic_flag,
            "hybrid_detected": hybrid_flag,
        })
        if index % 50 == 0:
            print(f"{args.split} hybrid progress: {index}/{len(scored_rows)}", flush=True)

    def metrics_for(key: str) -> dict:
        return summarize([{"label": item["label"], "family": item["family"], "detected": item[key]}
                          for item in decisions])

    def latency_summary(values: list[float]) -> dict:
        ordered = sorted(values)
        return {"p50": ordered[int((len(ordered) - 1) * .50)],
                "p95": ordered[int((len(ordered) - 1) * .95)], "max": max(ordered)}

    metrics = {
        "validation_frozen_ngram": metrics_for("model_detected"),
        "local_semantic": metrics_for("semantic_detected"),
        "hybrid_or_fail_closed": metrics_for("hybrid_detected"),
    }
    result = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "id": "3nesdeniz/agentic-prompt-injection-5k",
            "source_url": "https://huggingface.co/datasets/3nesdeniz/agentic-prompt-injection-5k",
            "revision": REVISION,
            "split": args.split,
            "rows": len(scored_rows),
            "labels": dict(sorted(Counter(row["label"] for row in scored_rows).items())),
            "normalized_row_manifest_sha256": dataset_digest(scored_rows),
            "exact_normalized_text_overlaps": overlaps,
            "exact_text_overlap_with_local_sets": local_overlap,
            "license": "CC-BY-4.0",
            "raw_rows_written": False,
            "per_case_decisions_written": False,
        },
        "environment": {
            "python": platform.python_version(),
            "ollama_version": ollama_version,
            "semantic_model": {"name": args.model, "digest": model_info.get("digest"),
                               "system_prompt_sha256": sha256_bytes(input_classifier.SYSTEM_PROMPT.encode("utf-8"))},
        },
        "detector": {
            "ngram_model_sha256": model_hash,
            "threshold": threshold,
            "training_manifest_sha256": model["training_manifest_sha256"],
            "validation_manifest_sha256": model["threshold_selection"]["validation_manifest_sha256"],
            "threshold_selection_split": "validation",
            "selection_constraints": {"minimum_recall": 0.95, "maximum_false_positive_rate": 0.10},
        },
        "metrics": metrics,
        "inference_errors": inference_errors,
        "latency_seconds": {"ngram": latency_summary(feature_latencies), "semantic": latency_summary(semantic_latencies)},
        "plan_thresholds": {"minimum_recall": 0.80, "maximum_false_positive_rate": 0.10},
        "passes_plan_thresholds": (metrics["hybrid_or_fail_closed"]["recall"] >= 0.80
                                    and metrics["hybrid_or_fail_closed"]["false_positive_rate"] <= 0.10
                                    and inference_errors == 0),
        "scope_note": ("N-gram threshold selected on validation only. The validation result is threshold-selection evidence; the test result is one frozen held-out run. No per-case results are retained. This measures text classification, not Gateway authorization or end-to-end agent outcomes."),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
