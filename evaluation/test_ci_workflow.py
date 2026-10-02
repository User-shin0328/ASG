from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CiWorkflowTests(unittest.TestCase):
    def test_required_security_and_evidence_gates_are_present(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("pypa/gh-action-pip-audit@v1.1.0", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("python -m evaluation.scan_git_history", workflow)
        self.assertEqual(workflow.count("aquasecurity/trivy-action@v0.36.0"), 5)
        self.assertEqual(workflow.count("exit-code: '1'"), 5)
        self.assertIn("Check PostgreSQL gosu code paths for Go vulnerabilities", workflow)
        self.assertIn("GOTOOLCHAIN=go1.24.6 /go/bin/govulncheck ./...", workflow)
        self.assertIn("vuln-type: os", workflow)
        for image in (
            "ai-agent-security-gateway-gateway:latest",
            "ai-agent-security-gateway-tool-sandbox:latest",
            "ai-agent-security-gateway-dashboard:latest",
            "ai-agent-security-gateway-demo-agent:latest",
            "ai-agent-security-gateway-postgres:latest",
        ):
            with self.subTest(image=image):
                self.assertIn(image, workflow)
        self.assertIn("reports/ci/unittest.log", workflow)
        self.assertIn("reports/ci/development-evaluation", workflow)


if __name__ == "__main__":
    unittest.main()
