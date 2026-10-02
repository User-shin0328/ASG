"""Frozen local n-gram detector; its verdict never grants Gateway permissions."""
from __future__ import annotations

import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path


MODEL_PATH = Path(__file__).resolve().parent / "models" / "agentic5k-bernoulli-charword-v1-r95b.json"
EXPECTED_DATASET_REVISION = "e658d94"
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
SPACE_RE = re.compile(r"\s+")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def features(text: str) -> set[str]:
    lowered = SPACE_RE.sub(" ", text.casefold().strip())
    tokens = TOKEN_RE.findall(lowered)
    result = {"w:" + token for token in tokens}
    result.update("b:" + left + " " + right for left, right in zip(tokens, tokens[1:]))
    for size in (3, 4, 5):
        result.update("c" + str(size) + ":" + lowered[index:index + size]
                      for index in range(max(0, len(lowered) - size + 1)))
    return result


@lru_cache(maxsize=4)
def load_model(path: str | Path = MODEL_PATH, require_validation_threshold: bool = True) -> tuple[dict, str]:
    model_path = Path(path)
    model = json.loads(model_path.read_text(encoding="utf-8"))
    recorded = model.get("model_sha256")
    payload = {key: value for key, value in model.items() if key != "model_sha256"}
    canonical = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    actual = sha256_bytes(canonical)
    if not isinstance(recorded, str) or actual != recorded:
        raise ValueError("frozen n-gram model integrity hash did not match")
    if model.get("source_revision") != EXPECTED_DATASET_REVISION or model.get("training_split") != "train":
        raise ValueError("frozen n-gram model provenance did not match")
    if require_validation_threshold and model.get("threshold_selection", {}).get("split") != "validation":
        raise ValueError("frozen n-gram threshold was not selected on validation")
    if not isinstance(model.get("weights"), dict) or not math.isfinite(model.get("threshold", math.nan)):
        raise ValueError("frozen n-gram model schema was invalid")
    return model, recorded


def score_text(text: str, model: dict | None = None) -> float:
    if not isinstance(text, str) or len(text) > 20000:
        raise ValueError("text must be a string of at most 20000 characters")
    if model is None:
        model, _ = load_model()
    return model["baseline_log_odds"] + sum(
        model["weights"].get(feature, 0.0) for feature in features(text)
    )


def classify_untrusted_text_ngram(text: str) -> tuple[str, float, str]:
    model, model_hash = load_model()
    score = score_text(text, model)
    return ("malicious" if score >= model["threshold"] else "benign", score, model_hash)
