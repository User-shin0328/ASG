from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from evaluation.scan_git_history import scan_history


class GitHistoryScanTests(unittest.TestCase):
    def make_repo(self, root: Path, content: str) -> None:
        subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
        (root / "fixture.txt").write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", "fixture.txt"], cwd=root, check=True)
        subprocess.run(["git", "commit", "--quiet", "-m", "fixture"], cwd=root, check=True)

    def test_scans_reachable_blobs_without_retaining_secret_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret_like_value = "ghp_" + ("A" * 30)
            self.make_repo(root, f"credential={secret_like_value}\n")

            result = scan_history(root)

            self.assertEqual(result["unique_blobs_scanned"], 1)
            self.assertEqual(len(result["matching_blobs"]), 1)
            self.assertIn("github-token", result["matching_blobs"][0]["pattern_classes"])
            self.assertNotIn(secret_like_value, str(result))
            self.assertFalse(result["raw_matches_retained"])

    def test_clean_history_has_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, "fictional demonstration fixture\n")

            result = scan_history(root)

            self.assertEqual(result["matching_blobs"], [])
            self.assertEqual(result["unique_blobs_scanned"], 1)


if __name__ == "__main__":
    unittest.main()
