import tempfile
import unittest
from email.message import Message
from pathlib import Path

from scripts.audit_dependency_licenses import audit, normalize_name, parse_lock


class DependencyLicenseAuditTests(unittest.TestCase):
    def test_normalizes_package_names(self):
        self.assertEqual(normalize_name("Typing_Extensions"), "typing-extensions")

    def test_parses_locked_name_version_and_extras(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "requirements.lock"
            lock.write_text("psycopg[binary]==3.3.6\n# comment\n", encoding="utf-8")
            self.assertEqual(parse_lock(lock), [("psycopg", "3.3.6")])

    def test_passes_when_locked_package_version_and_license_metadata_exist(self):
        class Distribution:
            name = "psycopg"
            version = "3.3.6"
            files = []
            metadata = Message()
            metadata["Name"] = "psycopg"
            metadata["License-Expression"] = "LGPL-3.0-only"
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "requirements.lock"
            lock.write_text("psycopg==3.3.6\n", encoding="utf-8")
            report = audit(lock, [Distribution()])
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["packages_missing_license_metadata"], [])

    def test_fails_when_locked_package_is_missing_or_unlicensed(self):
        class Distribution:
            name = "psycopg"
            version = "3.3.6"
            files = []
            metadata = Message()
            metadata["Name"] = "psycopg"
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "requirements.lock"
            lock.write_text("psycopg==3.3.6\ntyping-extensions==4.16.0\n", encoding="utf-8")
            report = audit(lock, [Distribution()])
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["missing_locked_packages"], ["typing-extensions"])
        self.assertEqual(report["packages_missing_license_metadata"], ["psycopg"])


if __name__ == "__main__":
    unittest.main()
