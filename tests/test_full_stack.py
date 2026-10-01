import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from demo_agent.deterministic import call
from gateway.app.core import Gateway
from gateway.app.main import Handler as GatewayHandler
from tool_sandbox import app as sandbox


class FullStackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.p_db = patch.object(sandbox, "DATABASE", str(Path(self.temp.name) / "tools.sqlite3"))
        self.p_token = patch.object(sandbox, "TOKEN", "s" * 48)
        self.p_db.start()
        self.p_token.start()
        self.tool_server = ThreadingHTTPServer(("127.0.0.1", 0), sandbox.Handler)
        self.tool_thread = threading.Thread(target=self.tool_server.serve_forever, daemon=True)
        self.tool_thread.start()
        self.gateway = Gateway(":memory:", {"agent-alice": "a" * 40, "reviewer-demo": "r" * 40}, f"http://127.0.0.1:{self.tool_server.server_port}", "s" * 48)
        GatewayHandler.gateway = self.gateway
        self.api_server = ThreadingHTTPServer(("127.0.0.1", 0), GatewayHandler)
        self.api_thread = threading.Thread(target=self.api_server.serve_forever, daemon=True)
        self.api_thread.start()
        self.base = f"http://127.0.0.1:{self.api_server.server_port}"

    def tearDown(self):
        self.api_server.shutdown()
        self.api_server.server_close()
        self.api_thread.join(timeout=2)
        self.tool_server.shutdown()
        self.tool_server.server_close()
        self.tool_thread.join(timeout=2)
        self.gateway.db.close()
        self.p_token.stop()
        self.p_db.stop()
        self.temp.cleanup()

    def test_end_to_end_read_review_and_submit_to_simulated_outbox(self):
        self.assertEqual(call(self.base, "", "GET", "/health/ready")["status"], "ready")
        headers = {"Idempotency-Key": "full-read"}
        read = call(self.base, "a" * 40, "POST", "/v1/actions", {"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-alice-001"}}, headers["Idempotency-Key"])
        self.assertEqual(read["state"], "SUCCEEDED")

        saved = call(self.base, "a" * 40, "POST", "/v1/actions", {"task_id": "task-alice-001", "tool": "save_summary", "arguments": {"document_id": "report-alice-001", "content": "Full-stack fictional summary."}}, "full-save")
        artifact_id = saved["result"]["result"]["artifact_id"]
        pending = call(self.base, "a" * 40, "POST", "/v1/actions", {"task_id": "task-alice-001", "tool": "send_report", "arguments": {"artifact_id": artifact_id, "destination_id": "internal-review-outbox"}}, "full-send")
        self.assertEqual(pending["state"], "PENDING_APPROVAL")

        approvals = call(self.base, "r" * 40, "GET", "/v1/approvals")
        self.assertEqual(approvals["items"][0]["review_snapshot"]["content"], "Full-stack fictional summary.")
        decided = call(self.base, "r" * 40, "POST", f"/v1/approvals/{pending['approval_id']}/decision", {"decision": "approve"})
        self.assertEqual(decided["state"], "APPROVED")
        done = call(self.base, "a" * 40, "POST", f"/v1/actions/{pending['action_id']}/execute")
        self.assertEqual(done["state"], "SUCCEEDED")
        self.assertEqual(done["result"]["result"]["status"], "submitted_to_mock_outbox")

        c = sandbox.connect()
        try:
            self.assertEqual(c.execute("SELECT count(*) FROM outbox").fetchone()[0], 1)
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
