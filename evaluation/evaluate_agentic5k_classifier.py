"""Score a frozen local classifier on the pinned test split exactly once."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from evaluation.metrics import summarize
from evaluation.run_agentic5k_external import REVISION, dataset_digest, fetch_rows
from demo_agent.ngram_classifier import features, load_model


ROOT = Path(__file__).resolve().parents[1]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new path")
    model, model_hash = load_model(args.model, require_validation_threshold=False)

    train_rows = fetch_rows("train")
    validation_rows = fetch_rows("validation")
    test_rows = fetch_rows("test")
    digest = lambda row: sha256_bytes(row["text"].casefold().strip().encode("utf-8"))
    train_hashes = {digest(row) for row in train_rows}
    validation_hashes = {digest(row) for row in validation_rows}
    test_hashes = {digest(row) for row in test_rows}
    overlaps = {
        "train_vs_validation": len(train_hashes & validation_hashes),
        "train_vs_test": len(train_hashes & test_hashes),
        "validation_vs_test": len(validation_hashes & test_hashes),
    }
    if any(overlaps.values()):
        raise SystemExit(f"Exact normalized-text overlap across dataset splits: {overlaps}")
    if dataset_digest(train_rows) != model.get("training_manifest_sha256"):
        raise SystemExit("Training manifest changed since model freeze")
    if len(validation_rows) != 467 or len(test_rows) != 545:
        raise SystemExit("Pinned validation/test row counts changed")

    weights = model["weights"]
    baseline = model["baseline_log_odds"]
    threshold = model["threshold"]
    decisions = []
    durations = []
    for index, row in enumerate(test_rows, 1):
        started = time.perf_counter()
        score = baseline + sum(weights.get(feature, 0.0) for feature in features(row["text"]))
        durations.append(time.perf_counter() - started)
        decisions.append({
            "label": row["label"],
            "family": row["family"],
            "detected": score >= threshold,
        })
        if index % 100 == 0:
            print(f"frozen classifier progress: {index}/{len(test_rows)}", flush=True)

    metrics = summarize(decisions)
    ordered = sorted(durations)
    metrics["latency_seconds"] = {
        "p50": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.5))],
        "p95": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.95))],
        "max": max(ordered),
    }
    result = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "id": "3nesdeniz/agentic-prompt-injection-5k",
            "source_url": "https://huggingface.co/datasets/3nesdeniz/agentic-prompt-injection-5k",
            "revision": REVISION,
            "split": "test",
            "rows": len(test_rows),
            "normalized_row_manifest_sha256": dataset_digest(test_rows),
            "exact_normalized_text_overlaps": overlaps,
            "license": "CC-BY-4.0",
            "raw_rows_written": False,
            "per_case_decisions_written": False,
        },
        "model": {
            "sha256": model_hash,
            "type": model["model_type"],
            "training_split": "train",
            "validation_threshold_split": "validation",
            "threshold": threshold,
            "vocabulary_size": model["vocabulary_size"],
            "training_manifest_sha256": model["training_manifest_sha256"],
        },
        "plan_thresholds": {"minimum_recall": 0.80, "maximum_false_positive_rate": 0.10},
        "metrics": metrics,
        "passes_plan_thresholds": metrics["recall"] >= 0.80 and metrics["false_positive_rate"] <= 0.10,
        "scope_note": "Frozen classifier evaluated once on the test split after threshold selection on validation. This measures text classification only, not Gateway authorization or end-to-end agent outcomes.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
