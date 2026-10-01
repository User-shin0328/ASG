"""Scan a `docker export` filesystem archive for configured high-confidence secrets."""
from __future__ import annotations

import re
import sys
import tarfile
from pathlib import Path

PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "provider-token": re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    "github-token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "aws-access-key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
}


def scan_archive(archive_path: Path) -> list[tuple[str, str]]:
    findings = []
    with tarfile.open(archive_path, mode="r:*") as archive:
        for member in archive:
            if not member.isfile():
                continue
            stream = archive.extractfile(member)
            if stream is None:
                continue
            data = stream.read()
            for kind, pattern in PATTERNS.items():
                if pattern.search(data):
                    findings.append((member.name, kind))
    return findings


def main(argv: list[str] | None = None) -> int:
    paths = [Path(item) for item in (argv if argv is not None else sys.argv[1:])]
    if not paths:
        print("Usage: python -m evaluation.scan_image_archive <docker-export.tar> [...]")
        return 2
    failed = False
    for path in paths:
        if not path.is_file():
            print(f"Archive not found: {path}")
            failed = True
            continue
        findings = scan_archive(path)
        if findings:
            failed = True
            for member, kind in findings:
                print(f"Possible {kind} in {path.name}:{member}")
        else:
            print(f"No configured high-confidence secret patterns in {path.name}.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
