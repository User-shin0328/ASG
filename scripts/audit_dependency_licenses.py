"""Inventory locked Python package licenses using installed distribution metadata."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import sys
from pathlib import Path


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_lock(path: Path) -> list[tuple[str, str | None]]:
    requirements: list[tuple[str, str | None]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?(?:\s*==\s*([A-Za-z0-9_.+!-]+))?", line)
        if not match:
            raise ValueError(f"Unsupported lock requirement syntax: {line}")
        requirements.append((normalize_name(match.group(1)), match.group(2)))
    return requirements


def audit(lock_path: Path, distributions=None) -> dict[str, object]:
    locked = parse_lock(lock_path)
    installed = {
        normalize_name(dist.metadata.get("Name") or dist.name): dist
        for dist in (distributions if distributions is not None else importlib.metadata.distributions())
    }
    missing = [name for name, _ in locked if name not in installed]
    version_mismatches = [
        {"name": name, "expected": version, "found": installed[name].version}
        for name, version in locked
        if name in installed and version and installed[name].version != version
    ]
    packages: list[dict[str, object]] = []
    missing_license_metadata: list[str] = []
    for name in sorted(installed):
        dist = installed[name]
        metadata = dist.metadata
        classifiers = [value for value in metadata.get_all("Classifier", []) if value.startswith("License ::")]
        expression = metadata.get("License-Expression")
        legacy_license = metadata.get("License")
        if not (expression or legacy_license or classifiers):
            missing_license_metadata.append(name)
        license_files = [str(item) for item in (dist.files or [])
                         if any(token in str(item).lower() for token in ("license", "copying", "notice"))]
        packages.append({
            "name": metadata.get("Name") or name,
            "version": dist.version,
            "license_expression": expression,
            "license": legacy_license,
            "license_classifiers": classifiers,
            "license_files": license_files,
        })
    return {
        "lockfile": str(lock_path),
        "locked_requirements": [{"name": name, "version": version} for name, version in locked],
        "installed_packages": packages,
        "missing_locked_packages": missing,
        "version_mismatches": version_mismatches,
        "packages_missing_license_metadata": missing_license_metadata,
        "result": "PASS" if not (missing or version_mismatches or missing_license_metadata) else "FAIL",
        "limitations": [
            "License metadata and files are reported as supplied by installed distributions.",
            "This inventory does not determine legal compatibility or scan operating-system packages.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("requirements.lock"))
    args = parser.parse_args()
    try:
        result = audit(args.lock)
    except (OSError, ValueError) as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
