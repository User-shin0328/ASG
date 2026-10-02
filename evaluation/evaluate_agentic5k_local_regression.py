"""Measure a frozen external candidate against existing local corpora."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from evaluation.evaluate_agentic5k_classifier import load_model
from evaluation.metrics import summarize
from evaluation.train_agentic5k_classifier import features


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new result path")
    model, model_hash = load_model(args.model)
    corpus_paths = [ROOT / "evaluation/datasets/dev.jsonl", *sorted((ROOT / "evaluation/datasets").glob("heldout-v*.jsonl"))]
    results = {}
    for path in corpus_paths:
        cases = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            label = row.get("label")
            if label not in {"malicious", "normal"}:
                continue
            score = model["baseline_log_odds"] + sum(
                model["weights"].get(feature, 0.0) for feature in features(row["text"])
            )
            cases.append({"label": label, "family": row.get("family", "local"),
                          "detected": score >= model["threshold"]})
        if cases:
            results[str(path.relative_to(ROOT)).replace("\\", "/")] = summarize(cases)
    output = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_model_sha256": model_hash,
        "threshold": model["threshold"],
        "local_corpora": results,
        "raw_rows_written": False,
        "per_case_decisions_written": False,
        "scope_note": "Offline compatibility check only. Local corpora are project-authored and previously observed; this is not independent generalization evidence.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
