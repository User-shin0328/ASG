"""Replay a frozen n-gram candidate against retained local semantic decisions."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from demo_agent.ngram_classifier import features, load_model
from evaluation.metrics import summarize


ROOT = Path(__file__).resolve().parents[1]
CORPORA = {
    "heldout-v5": ("evaluation/datasets/heldout-v5.jsonl", "evaluation/results/llm-classifier-v5-heldout"),
    "heldout-v6-task-context": ("evaluation/datasets/heldout-v6.jsonl", "evaluation/results/llm-classifier-v6-task-context-recheck-2026-10-02"),
    "heldout-v7": ("evaluation/datasets/heldout-v7.jsonl", "evaluation/results/llm-classifier-v7-preregistered"),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new result path")
    model, model_hash = load_model(args.model)
    corpora = {}
    for name, (dataset_rel, result_rel) in CORPORA.items():
        rows = [json.loads(line) for line in (ROOT / dataset_rel).read_text(encoding="utf-8").splitlines() if line.strip()]
        decisions = [json.loads(line) for line in (ROOT / result_rel / "decisions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        environment = json.loads((ROOT / result_rel / "environment.json").read_text(encoding="utf-8"))
        by_id = {item.get("case_id"): item for item in decisions}
        if len(by_id) != len(rows) or set(by_id) != {row.get("case_id") for row in rows}:
            raise SystemExit(f"Semantic decision IDs did not match {name}")
        semantic_cases = []
        ngram_cases = []
        hybrid_cases = []
        for row in rows:
            decision = by_id[row["case_id"]]
            text_hash = sha256_bytes(row["text"].encode("utf-8"))
            if decision.get("content_hash") != text_hash or decision.get("label") != row["label"]:
                raise SystemExit(f"Semantic result did not bind to source row {row['case_id']}")
            ngram_flag = model["baseline_log_odds"] + sum(
                model["weights"].get(feature, 0.0) for feature in features(row["text"])
            ) >= model["threshold"]
            label = row["label"]
            semantic_flag = bool(decision["detected"])
            fail_closed_hybrid = semantic_flag or ngram_flag or decision.get("error") is not None
            semantic_cases.append({"label": label, "family": row.get("family"), "detected": semantic_flag})
            ngram_cases.append({"label": label, "family": row.get("family"), "detected": ngram_flag})
            hybrid_cases.append({"label": label, "family": row.get("family"), "detected": fail_closed_hybrid})
        corpora[name] = {
            "cases": len(rows),
            "dataset_manifest_sha256": sha256_bytes(json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")),
            "semantic_prompt_sha256": environment.get("manifest", {}).get("system_prompt_sha256"),
            "semantic_model_digest": environment.get("manifest", {}).get("model_digest"),
            "semantic": summarize(semantic_cases),
            "ngram": summarize(ngram_cases),
            "hybrid_or_fail_closed": summarize(hybrid_cases),
        }
    result = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_model_sha256": model_hash,
        "threshold": model["threshold"],
        "corpora": corpora,
        "raw_rows_written": False,
        "per_case_decisions_written": False,
        "scope_note": "Offline replay of a frozen n-gram model against previously retained local semantic decisions, bound to each exact source row by ID, label, and content hash. It is compatibility evidence, not a fresh or independent LLM run.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
