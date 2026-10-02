"""Evaluate local input detectors on deepset's public prompt-injection test split.

The source Parquet file is temporary by default; only aggregate metrics and
content hashes are written. This direct-prompt set is diagnostic and does not
replace the project's indirect-document or tool-outcome evaluations.
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
from datetime import datetime, timezone
from pathlib import Path

from demo_agent.input_classifier import SYSTEM_PROMPT, classify_untrusted_text
from evaluation.metrics import summarize
from gateway.app.core import INSPECTION_SCANNER_VERSION, scan_untrusted_text


ROOT = Path(__file__).resolve().parents[1]
DATASET_URL = (
    "https://huggingface.co/datasets/deepset/prompt-injections/resolve/4928447/"
    "data/test-00000-of-00001-701d16158af87368.parquet"
)
DATASET_SHA256 = "39ac797cabc157eeed58435a08593b2952bb6cb16fc394a2d383f447cc7b246e"
EXPECTED_ROWS = 116


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rows(path: Path) -> list[tuple[str, str]]:
    try:
        import duckdb
    except ImportError as exc:
        raise SystemExit("Install the optional reader with: python -m pip install -r evaluation/requirements-external.txt") from exc
    rows = duckdb.connect().execute("SELECT text, label FROM read_parquet(?)", [str(path)]).fetchall()
    if len(rows) != EXPECTED_ROWS or any(not isinstance(text, str) or label not in (0, 1) for text, label in rows):
        raise SystemExit("External split shape did not match the pinned dataset metadata")
    if len({text.casefold().strip() for text, _ in rows}) != len(rows):
        raise SystemExit("External split contains duplicate normalized text")
    return [(text, "malicious" if label == 1 else "normal") for text, label in rows]


def evaluate_rules(rows: list[tuple[str, str]]) -> dict:
    results = [{"label": label, "detected": bool(scan_untrusted_text(text))} for text, label in rows]
    metrics = summarize(results)
    metrics["scanner_version"] = INSPECTION_SCANNER_VERSION
    return metrics


def evaluate_semantic(rows: list[tuple[str, str]], base: str, model: str, timeout: int) -> dict:
    results = []
    latencies = []
    errors = 0
    for text, label in rows:
        detected, elapsed, error = classify_untrusted_text(base, model, text, timeout)
        latencies.append(elapsed)
        errors += error is not None
        results.append({"label": label, "detected": detected == "malicious"})
    metrics = summarize(results)
    ordered = sorted(latencies)
    metrics["inference_errors"] = errors
    metrics["latency_seconds"] = {
        "p50": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.5))],
        "p95": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.95))],
        "max": max(ordered),
    }
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-file", type=Path, help="Use an already downloaded Parquet file instead of fetching it")
    parser.add_argument("--mode", choices=("all", "rules", "semantic"), default="all")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    parser.add_argument("--ollama", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--output", type=Path, help="Optional new JSON file for metrics only; it is never overwritten")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        raise SystemExit("timeout must be between 1 and 120 seconds")
    if args.output and args.output.exists():
        raise SystemExit("Output already exists; choose a new result path")

    with tempfile.TemporaryDirectory(prefix="deepset-prompt-injections-") as temp_dir:
        parquet = args.dataset_file.resolve() if args.dataset_file else Path(temp_dir) / "test.parquet"
        if not args.dataset_file:
            request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "AI-Agent-Security-Gateway-evaluation/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response, parquet.open("wb") as target:
                while block := response.read(1024 * 1024):
                    target.write(block)
        observed_hash = sha256(parquet)
        if observed_hash != DATASET_SHA256:
            raise SystemExit("Dataset SHA-256 did not match the pinned test split")
        rows = load_rows(parquet)
        labels = {label: sum(item[1] == label for item in rows) for label in ("normal", "malicious")}
        local_texts = set()
        for path in [ROOT / "evaluation/datasets/dev.jsonl", *sorted((ROOT / "evaluation/datasets").glob("heldout-v*.jsonl"))]:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    local_texts.add(json.loads(line)["text"].casefold().strip())
        overlaps = sum(text.casefold().strip() in local_texts for text, _ in rows)

        metrics = {}
        if args.mode in {"all", "rules"}:
            metrics["rules"] = evaluate_rules(rows)
        model_manifest = None
        if args.mode in {"all", "semantic"}:
            version_url = args.ollama.rstrip("/") + "/api/version"
            tags_url = args.ollama.rstrip("/") + "/api/tags"
            with urllib.request.urlopen(version_url, timeout=5) as response:
                version = json.loads(response.read())
            with urllib.request.urlopen(tags_url, timeout=5) as response:
                models = json.loads(response.read()).get("models", [])
            model_info = next((entry for entry in models if entry.get("name") == args.model), None)
            if model_info is None:
                raise SystemExit(f"Requested local model is not installed: {args.model}")
            model_manifest = {
                "name": args.model,
                "digest": model_info.get("digest"),
                "ollama_version": version.get("version"),
                "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
            }
            metrics["semantic"] = evaluate_semantic(rows, args.ollama, args.model, args.timeout)

        result = {
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "dataset": {
                "id": "deepset/prompt-injections",
                "split": "test",
                "revision": "4928447",
                "url": DATASET_URL,
                "sha256": observed_hash,
                "rows": len(rows),
                "labels": labels,
                "exact_text_overlap_with_local_sets": overlaps,
                "repository_license": "Apache-2.0",
                "dataset_card_license": "CC-BY-4.0",
                "raw_rows_written": False,
            },
            "environment": {"python": platform.python_version(), "model": model_manifest},
            "metrics": metrics,
            "scope_note": "Direct-prompt classifier data; diagnostic only, not an indirect-document or tool-outcome evaluation.",
        }
        serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized, encoding="utf-8")
        print(serialized, end="")


if __name__ == "__main__":
    main()
