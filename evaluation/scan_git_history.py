"""Scan reachable Git blobs for the repository's high-confidence secret patterns."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from scripts.check_secrets import PATTERNS


ROOT = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    command = ["git", "-c", f"safe.directory={root.as_posix()}", *args]
    return subprocess.check_output(command, cwd=root, input=input_bytes, stderr=subprocess.PIPE)


def _reachable_blob_ids(root: Path) -> tuple[list[str], int]:
    lines = _git(root, "rev-list", "--objects", "--all").decode("utf-8").splitlines()
    object_ids = list(dict.fromkeys(line.split(" ", 1)[0] for line in lines if line))
    request = ("\n".join(object_ids) + "\n").encode("ascii")
    headers = _git(root, "cat-file", "--batch-check", input_bytes=request).decode("ascii").splitlines()
    blob_ids = []
    for header in headers:
        fields = header.split()
        if len(fields) == 3 and fields[1] == "blob":
            blob_ids.append(fields[0])
    return blob_ids, len(object_ids)


def _scan_batch(root: Path, blob_ids: list[str]) -> list[dict[str, object]]:
    if not blob_ids:
        return []
    request = ("\n".join(blob_ids) + "\n").encode("ascii")
    content = _git(root, "cat-file", "--batch", input_bytes=request)
    patterns = {
        name: re.compile(pattern.pattern.encode("ascii"), pattern.flags & ~re.UNICODE)
        for name, pattern in PATTERNS.items()
    }
    matches: list[dict[str, object]] = []
    offset = 0
    while offset < len(content):
        header_end = content.find(b"\n", offset)
        if header_end < 0:
            raise ValueError("Git returned a truncated object header")
        fields = content[offset:header_end].split()
        if len(fields) != 3 or fields[1] != b"blob":
            raise ValueError("Git returned an unexpected object while reading blobs")
        object_id, size = fields[0].decode("ascii"), int(fields[2])
        body_start = header_end + 1
        body_end = body_start + size
        if body_end >= len(content) or content[body_end:body_end + 1] != b"\n":
            raise ValueError("Git returned a truncated blob")
        body = content[body_start:body_end]
        names = [name for name, pattern in patterns.items() if pattern.search(body)]
        if names:
            matches.append({"object_id": object_id, "pattern_classes": names})
        offset = body_end + 1
    return matches


def scan_history(root: Path = ROOT) -> dict[str, object]:
    root = root.resolve()
    blob_ids, reachable_objects = _reachable_blob_ids(root)
    matches = _scan_batch(root, blob_ids)
    remotes = _git(root, "remote").decode("utf-8").splitlines()
    return {
        "commit": _git(root, "rev-parse", "HEAD").decode("ascii").strip(),
        "reachable_objects": reachable_objects,
        "unique_blobs_scanned": len(blob_ids),
        "configured_high_confidence_pattern_classes": list(PATTERNS),
        "matching_blobs": matches,
        "remote_configured": bool(remotes),
        "raw_matches_retained": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write JSON evidence to this file instead of stdout")
    args = parser.parse_args()
    try:
        result = scan_history()
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError) as exc:
        print(f"Git history scan failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if result["matching_blobs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
