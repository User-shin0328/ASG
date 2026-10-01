from __future__ import annotations

import argparse
import json
import hashlib
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gateway.app.core import scan_untrusted_text
from evaluation.metrics import summarize


def load_dataset(path: Path, kind: str) -> list[dict]:
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read a valid JSONL evaluation dataset: {exc}") from exc
    required = {"case_id", "label", "source", "text"}
    if not rows or any(not isinstance(row, dict) or not required <= row.keys() for row in rows):
        raise SystemExit("Every evaluation row must contain case_id, label, source, and text")
    if any(row["label"] not in {"normal", "malicious"} or not isinstance(row["text"], str) or not row["text"].strip() for row in rows):
        raise SystemExit("Evaluation rows contain an invalid label or empty text")
    case_ids = [row["case_id"] for row in rows]
    if any(not isinstance(case_id, str) or not case_id for case_id in case_ids) or len(set(case_ids)) != len(case_ids):
        raise SystemExit("Evaluation case IDs must be nonempty and unique")
    normalized_texts = [row["text"].casefold().strip() for row in rows]
    if len(set(normalized_texts)) != len(normalized_texts):
        raise SystemExit("Evaluation texts must be unique within a dataset")
    if kind == "heldout":
        labels = {label: sum(row["label"] == label for row in rows) for label in ("normal", "malicious")}
        if labels != {"normal": 50, "malicious": 50}:
            raise SystemExit("The held-out set must contain exactly 50 normal and 50 malicious cases")
        if any(not isinstance(row.get("family"), str) or not row["family"] for row in rows):
            raise SystemExit("Every held-out case must identify its attack/normal family")
        family_labels: dict[str, set[str]] = {}
        family_counts: dict[str, int] = {}
        for row in rows:
            family = row["family"]
            family_labels.setdefault(family, set()).add(row["label"])
            family_counts[family] = family_counts.get(family, 0) + 1
        if len(family_counts) != 20 or set(family_counts.values()) != {5} or any(len(labels) != 1 for labels in family_labels.values()):
            raise SystemExit("Held-out data must contain 20 label-pure families with five cases each")
        dev_path = ROOT / "evaluation/datasets/dev.jsonl"
        dev_texts = {json.loads(line)["text"].casefold().strip() for line in dev_path.read_text(encoding="utf-8").splitlines() if line.strip()}
        if any(row["text"].casefold().strip() in dev_texts for row in rows):
            raise SystemExit("Held-out cases must not duplicate development-set texts")
        for prior_path in (ROOT / "evaluation/datasets").glob("heldout-v*.jsonl"):
            if path.resolve() == prior_path.resolve():
                continue
            prior_texts = {json.loads(line)["text"].casefold().strip() for line in prior_path.read_text(encoding="utf-8").splitlines() if line.strip()}
            if any(row["text"].casefold().strip() in prior_texts for row in rows):
                raise SystemExit(f"A new held-out set must not duplicate prior set: {prior_path.name}")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "evaluation/datasets/dev.jsonl")
    parser.add_argument("--dataset-kind", choices=("development", "heldout"), default="development")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    out = args.output_dir or ROOT / "reports" / run_id
    out.mkdir(parents=True, exist_ok=False)
    rows = load_dataset(args.dataset, args.dataset_kind)
    results = []
    for row in rows:
        hits = scan_untrusted_text(row["text"])
        results.append({"case_id": row["case_id"], "label": row["label"], "source": row["source"], "family": row.get("family", "unspecified"), "scanner_version": "rules-v1", "detected": bool(hits), "reason_codes": ["PROMPT_INJECTION_PATTERN"] if hits else [], "content_hash": hashlib.sha256(row["text"].encode()).hexdigest()})
    metrics = summarize(results)
    metrics["dataset"] = str(args.dataset.relative_to(ROOT)) if args.dataset.is_relative_to(ROOT) else args.dataset.name
    dataset_hash = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    metrics["dataset_sha256"] = dataset_hash
    metrics["dataset_kind"] = args.dataset_kind
    metrics["note"] = ("Author-created synthetic held-out set; results are not an independent benchmark or an LLM behavior result." if args.dataset_kind == "heldout" else "Synthetic development dataset only; not a held-out or LLM behavior result.")
    manifest = {"dataset": metrics["dataset"], "kind": args.dataset_kind, "sha256": dataset_hash, "cases": len(rows), "label_counts": {label: sum(r["label"] == label for r in rows) for label in ("normal", "malicious")}, "families": sorted({r.get("family", "unspecified") for r in rows})}
    (out / "environment.json").write_text(json.dumps({"run_id": run_id, "python": platform.python_version(), "platform": platform.platform(), "started_at": datetime.now(timezone.utc).isoformat(), "scanner": "rules-v1", "mode": "deterministic-scan-only", "dataset_kind": args.dataset_kind, "dataset_sha256": dataset_hash}, indent=2), encoding="utf-8")
    (out / "dataset-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "decisions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (out / "summary.md").write_text("# Synthetic input-inspection run\n\n" + f"Run: `{run_id}`\n\n" + f"Cases: {metrics['cases']}\n\n" + f"Recall: {metrics['recall']}\n\nPrecision: {metrics['precision']}\n\nFalse-positive rate: {metrics['false_positive_rate']}\n\n" + metrics["note"] + "\n", encoding="utf-8")
    print(out)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
