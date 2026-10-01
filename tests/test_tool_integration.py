import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from gateway.app.core import Gateway
from tool_sandbox import app as sandbox


class ToolServiceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp.name) / "tool.sqlite3")
        self.patcher_db = patch.object(sandbox, "DATABASE", self.db_path)
        self.patcher_token = patch.object(sandbox, "TOKEN", "s" * 48)
        self.patcher_db.start()
        self.patcher_token.start()
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), sandbox.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.gateway = Gateway(":memory:", {"agent-alice": "a" * 40, "reviewer-demo": "r" * 40}, f"http://127.0.0.1:{self.http.server_port}", "s" * 48)
        self.alice = self.gateway.authenticate("a" * 40)
        self.reviewer = self.gateway.authenticate("r" * 40)

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)
        self.gateway.db.close()
        self.patcher_token.stop()
        self.patcher_db.stop()
        self.temp.cleanup()

    def test_live_http_tools_preserve_scope_and_approval_receipt(self):
        read = self.gateway.create_action(self.alice, {"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-alice-001"}}, "read-1")
        self.assertEqual(read["state"], "SUCCEEDED")
        self.assertIn("fictional", read["result"]["result"]["content"])

        save = self.gateway.create_action(self.alice, {"task_id": "task-alice-001", "tool": "save_summary", "arguments": {"document_id": "report-alice-001", "content": "A fictional approved summary."}}, "save-1")
        artifact_id = save["result"]["result"]["artifact_id"]
        send = self.gateway.create_action(self.alice, {"task_id": "task-alice-001", "tool": "send_report", "arguments": {"artifact_id": artifact_id, "destination_id": "internal-review-outbox"}}, "send-1")
        self.assertEqual(send["state"], "PENDING_APPROVAL")
        self.gateway.decide(self.reviewer, send["approval_id"], "approve")
        done = self.gateway.execute(self.alice, send["action_id"])
        self.assertEqual(done["state"], "SUCCEEDED")
        replay = self.gateway.execute(self.alice, send["action_id"])
        self.assertEqual(replay["result"]["result"]["status"], "submitted_to_mock_outbox")

        c = sandbox.connect()
        try:
            self.assertEqual(c.execute("SELECT count(*) n FROM outbox").fetchone()["n"], 1)
            self.assertEqual(c.execute("SELECT count(*) n FROM receipts").fetchone()["n"], 3)
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
