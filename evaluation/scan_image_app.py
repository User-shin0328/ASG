"""Scan an image's mounted application tree for the repository's high-confidence secret patterns."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("SCAN_ROOT", "/app"))
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "provider-token": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}


def main() -> int:
    if not ROOT.is_dir():
        print("Application scan root not found")
        return 2
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
            text = data.decode("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append((path.relative_to(ROOT).as_posix(), name))
    if findings:
        for path, name in findings:
            print(f"Possible {name}: {path}")
        return 1
    print(f"No configured high-confidence secret patterns in {ROOT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
