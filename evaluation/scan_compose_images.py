"""Export and scan the current local Compose images without starting them."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import tarfile

from evaluation.scan_image_archive import scan_archive

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("gateway", "migrate", "token-admin", "postgres", "tool-sandbox", "dashboard", "demo-agent")


def docker(docker_path: str, *args: str) -> str:
    result = subprocess.run([docker_path, *args], check=True, capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    return result.stdout.strip()


def scan_service(docker_path: str, service: str, image: str) -> dict[str, object]:
    image_id = docker(docker_path, "image", "inspect", "--format", "{{.Id}}", image)
    container_name = f"codex-image-scan-{service}-{uuid.uuid4().hex[:8]}"
    container_id = docker(docker_path, "create", "--name", container_name, image)
    try:
        with tempfile.TemporaryDirectory(prefix="codex-gateway-image-scan-") as temp_dir:
            archive_path = Path(temp_dir) / f"{service}.tar"
            docker(docker_path, "export", "--output", str(archive_path), container_id)
            findings = scan_archive(archive_path)
            with tarfile.open(archive_path, mode="r:*") as archive:
                filesystem_bytes = sum(member.size for member in archive if member.isfile())
        return {"image": image, "image_id": image_id, "filesystem_bytes": filesystem_bytes,
                "matches": len(findings), "findings": [{"path": path, "pattern": kind} for path, kind in findings]}
    finally:
        docker(docker_path, "rm", container_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docker", required=True, help="Path to the Docker CLI")
    parser.add_argument("--image-prefix", default="ai-agent-security-gateway-")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_commit = subprocess.run(["git", "-c", f"safe.directory={ROOT.as_posix()}",
                                    "rev-parse", "HEAD"], cwd=ROOT, check=True,
                                   capture_output=True, text=True, encoding="utf-8",
                                   errors="replace").stdout.strip()
    docker_version = docker(args.docker, "version", "--format", "{{.Server.Version}}")
    images = {service: scan_service(args.docker, service, f"{args.image_prefix}{service}:latest")
              for service in SERVICES}
    report = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "source_commit": source_commit,
        "docker_engine": docker_version,
        "method": "docker create + docker export; inspect every regular file in each merged image filesystem",
        "patterns": ["private-key", "provider-token", "github-token", "aws-access-key"],
        "images": images,
        "aggregate_filesystem_bytes": sum(int(item["filesystem_bytes"]) for item in images.values()),
        "aggregate_matches": sum(int(item["matches"]) for item in images.values()),
        "limitations": ["Only four configured high-confidence patterns were checked.",
                        "Docker export excludes mounted volume contents.",
                        "This is not a general vulnerability or malware scan."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_commit": source_commit, "images": len(images),
                      "aggregate_filesystem_bytes": report["aggregate_filesystem_bytes"],
                      "aggregate_matches": report["aggregate_matches"], "output": str(args.output)}, indent=2))
    return int(report["aggregate_matches"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
