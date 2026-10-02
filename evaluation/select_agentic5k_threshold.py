"""Select and freeze a stricter n-gram threshold on validation only."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from evaluation.evaluate_agentic5k_classifier import load_model
from evaluation.run_agentic5k_external import REVISION, dataset_digest, fetch_rows
from evaluation.train_agentic5k_classifier import features, summarize


TARGET_RECALL = 0.95
MAX_FPR = 0.10


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--result-output", type=Path, required=True)
    args = parser.parse_args()
    if args.model_output.exists() or args.result_output.exists():
        raise SystemExit("Output already exists; choose new paths")
    base_model, base_hash = load_model(args.base_model)
    rows = fetch_rows("validation")
    scores = [
        base_model["baseline_log_odds"]
        + sum(base_model["weights"].get(feature, 0.0) for feature in features(row["text"]))
        for row in rows
    ]
    labels = [row["label"] for row in rows]
    candidates = sorted(set(scores), reverse=True)
    candidates.append(math.nextafter(candidates[-1], -math.inf))
    eligible = []
    for threshold in candidates:
        metrics = summarize(labels, scores, threshold)
        if metrics["recall"] >= TARGET_RECALL and metrics["false_positive_rate"] <= MAX_FPR:
            eligible.append((threshold, metrics))
    if not eligible:
        raise SystemExit("No validation threshold met the candidate constraints")
    threshold, metrics = max(eligible, key=lambda item: item[0])

    model = dict(base_model)
    model["threshold"] = threshold
    model["threshold_selection"] = {
        "split": "validation",
        "validation_manifest_sha256": dataset_digest(rows),
        "minimum_recall": TARGET_RECALL,
        "maximum_false_positive_rate": MAX_FPR,
        "rule": "highest threshold satisfying both validation constraints",
    }
    model.pop("model_sha256", None)
    canonical = json.dumps(model, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    model_hash = sha256_bytes(canonical.encode("utf-8"))
    model["model_sha256"] = model_hash

    result = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "id": "3nesdeniz/agentic-prompt-injection-5k",
            "revision": REVISION,
        "split": "validation",
            "rows": len(rows),
            "normalized_row_manifest_sha256": dataset_digest(rows),
            "base_model_sha256": base_hash,
            "exact_text_overlap_with_local_sets": 0,
            "raw_rows_written": False,
            "per_case_decisions_written": False,
        },
        "selected_model_sha256": model_hash,
        "selected_threshold": threshold,
        "validation_metrics": metrics,
        "selection_constraints": {"minimum_recall": TARGET_RECALL, "maximum_false_positive_rate": MAX_FPR},
        "scope_note": "Threshold selected on validation only. The Qwen OR-combination has recall at least this model recall and FPR no greater than the Qwen validation FPR; it remains subject to the frozen external test run.",
    }
    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    args.result_output.parent.mkdir(parents=True, exist_ok=True)
    args.model_output.write_text(json.dumps(model, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    args.result_output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
