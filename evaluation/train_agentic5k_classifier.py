"""Train a lightweight Bernoulli n-gram detector from the pinned train split.

Raw samples remain in memory. The exported model contains vocabulary weights,
threshold, and source hashes only; validation chooses the threshold and the test
split is not read by this trainer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from demo_agent.ngram_classifier import features
from evaluation.run_agentic5k_external import REVISION, dataset_digest, fetch_rows, local_text_hashes


ROOT = Path(__file__).resolve().parents[1]
MIN_DOCUMENT_FREQUENCY = 2
MAX_FEATURES = 60000
TARGET_FPR = 0.10
TARGET_RECALL = 0.80


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def summarize(labels: list[str], scores: list[float], threshold: float) -> dict:
    tp = fp = fn = tn = 0
    for label, score in zip(labels, scores):
        predicted = score >= threshold
        if label == "malicious" and predicted:
            tp += 1
        elif label == "normal" and predicted:
            fp += 1
        elif label == "malicious":
            fn += 1
        else:
            tn += 1
    return {
        "cases": len(labels),
        "confusion": {"true_positive": tp, "false_positive": fp,
                      "false_negative": fn, "true_negative": tn},
        "recall": tp / (tp + fn) if tp + fn else None,
        "false_positive_rate": fp / (fp + tn) if fp + tn else None,
        "precision": tp / (tp + fp) if tp + fp else None,
    }


def select_threshold(labels: list[str], scores: list[float]) -> tuple[float, dict]:
    candidates = sorted(set(scores), reverse=True)
    candidates.append(math.nextafter(candidates[-1], -math.inf))
    feasible: list[tuple[float, float, float, dict]] = []
    for threshold in candidates:
        metrics = summarize(labels, scores, threshold)
        if metrics["false_positive_rate"] <= TARGET_FPR:
            feasible.append((metrics["recall"], -metrics["false_positive_rate"], threshold, metrics))
    best = max(feasible, key=lambda item: (item[0], item[1], item[2]))
    return best[2], best[3]


def train_weights(train_rows: list[dict]) -> tuple[float, dict[str, float]]:
    document_frequency: Counter[str] = Counter()
    class_frequency = {"normal": Counter(), "malicious": Counter()}
    class_docs = Counter()
    for row in train_rows:
        present = features(row["text"])
        label = row["label"]
        class_docs[label] += 1
        document_frequency.update(present)
        class_frequency[label].update(present)

    vocabulary = [feature for feature, count in document_frequency.items()
                  if count >= MIN_DOCUMENT_FREQUENCY]
    vocabulary.sort(key=lambda feature: (-document_frequency[feature], feature))
    vocabulary = vocabulary[:MAX_FEATURES]
    total_docs = len(train_rows)
    alpha = 1.0
    prior = math.log((class_docs["malicious"] + alpha) / (class_docs["normal"] + alpha))
    baseline = prior
    weights: dict[str, float] = {}
    for feature in vocabulary:
        p_mal = (class_frequency["malicious"][feature] + alpha) / (class_docs["malicious"] + 2 * alpha)
        p_norm = (class_frequency["normal"][feature] + alpha) / (class_docs["normal"] + 2 * alpha)
        baseline += math.log1p(-p_mal) - math.log1p(-p_norm)
        weights[feature] = (math.log(p_mal) - math.log1p(-p_mal)
                            - math.log(p_norm) + math.log1p(-p_norm))
    return baseline, weights


def score_rows(rows: list[dict], baseline: float, weights: dict[str, float]) -> list[float]:
    return [baseline + sum(weights.get(feature, 0.0) for feature in features(row["text"]))
            for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--result-output", type=Path, required=True)
    args = parser.parse_args()
    if args.model_output.exists() or args.result_output.exists():
        raise SystemExit("Output already exists; choose new paths")

    train_rows = fetch_rows("train")
    validation_rows = fetch_rows("validation")
    local_hashes = local_text_hashes()
    train_text_hashes = {sha256_bytes(row["text"].casefold().strip().encode("utf-8")) for row in train_rows}
    validation_text_hashes = {sha256_bytes(row["text"].casefold().strip().encode("utf-8")) for row in validation_rows}
    overlaps = {
        "train_vs_validation": len(train_text_hashes & validation_text_hashes),
        "train_vs_local_sets": len(train_text_hashes & local_hashes),
        "validation_vs_local_sets": len(validation_text_hashes & local_hashes),
    }
    if any(overlaps.values()):
        raise SystemExit(f"Exact normalized-text overlap found: {overlaps}")

    baseline, weights = train_weights(train_rows)
    validation_scores = score_rows(validation_rows, baseline, weights)
    threshold, validation_metrics = select_threshold(
        [row["label"] for row in validation_rows], validation_scores)
    accepted_on_validation = (
        validation_metrics["recall"] >= TARGET_RECALL
        and validation_metrics["false_positive_rate"] <= TARGET_FPR
    )

    model = {
        "model_type": "bernoulli-character-word-ngram-log-odds-v1",
        "source_dataset": "3nesdeniz/agentic-prompt-injection-5k",
        "source_url": "https://huggingface.co/datasets/3nesdeniz/agentic-prompt-injection-5k",
        "source_revision": REVISION,
        "license": "CC-BY-4.0",
        "attribution": "Enes Deniz, Agentic Prompt-Injection 5K (2026), CC-BY-4.0",
        "training_split": "train",
        "training_rows": len(train_rows),
        "training_manifest_sha256": dataset_digest(train_rows),
        "vocabulary_size": len(weights),
        "baseline_log_odds": baseline,
        "threshold": threshold,
        "weights": weights,
        "normalization": "Unicode casefold; collapse whitespace",
        "tokenizer": "Unicode alphanumeric word unigrams and adjacent bigrams",
        "character_ngrams": [3, 4, 5],
        "minimum_document_frequency": MIN_DOCUMENT_FREQUENCY,
        "maximum_features": MAX_FEATURES,
    }
    model_bytes = (json.dumps(model, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    model["model_sha256"] = sha256_bytes(model_bytes)
    model_bytes = (json.dumps(model, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

    result = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "id": "3nesdeniz/agentic-prompt-injection-5k",
            "revision": REVISION,
            "license": "CC-BY-4.0",
            "train_rows": len(train_rows),
            "validation_rows": len(validation_rows),
            "train_manifest_sha256": dataset_digest(train_rows),
            "validation_manifest_sha256": dataset_digest(validation_rows),
            "exact_normalized_text_overlaps": overlaps,
            "raw_rows_written": False,
        },
        "model": {
            "type": model["model_type"],
            "sha256": model["model_sha256"],
            "vocabulary_size": len(weights),
            "threshold": threshold,
        },
        "validation_metrics": validation_metrics,
        "plan_thresholds": {"minimum_recall": TARGET_RECALL, "maximum_false_positive_rate": TARGET_FPR},
        "passes_validation_thresholds": accepted_on_validation,
        "scope_note": "Threshold selected on validation only. The test split was not loaded or scored by this trainer. This is text classification, not Gateway authorization.",
    }
    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    args.result_output.parent.mkdir(parents=True, exist_ok=True)
    args.model_output.write_bytes(model_bytes)
    args.result_output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
