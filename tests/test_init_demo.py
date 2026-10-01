from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class DemoInitializationTests(unittest.TestCase):
    def test_postgres_init_script_uses_unix_line_endings(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "create_gateway_role.sh"
        contents = script.read_bytes()
        self.assertTrue(contents.startswith(b"#!/bin/sh\n"))
        self.assertNotIn(b"\r\n", contents)

    def test_reinitialization_preserves_existing_credentials_and_database_secrets(self):
        with tempfile.TemporaryDirectory(prefix="gateway-init-check-") as temp:
            target = Path(temp)
            command = [sys.executable, "-m", "scripts.init_demo", "--target-dir", str(target)]
            first = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            protected_files = [target / ".env", *sorted((target / "secrets").glob("*.txt"))]
            self.assertEqual(len(protected_files), 3)
            before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected_files}

            second = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected_files}
            self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
