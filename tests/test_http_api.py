import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from gateway.app.main import Handler
from tests.test_gateway import MockGateway


class HttpApiTests(unittest.TestCase):
    def setUp(self):
        self.gateway = MockGateway()
        Handler.gateway = self.gateway
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.gateway.db.close()

    def request(self, method, path, body=None, token=None, idem=None):
        c = http.client.HTTPConnection("127.0.0.1", self.base, timeout=3)
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = "Bearer " + token
        if idem:
            headers["Idempotency-Key"] = idem
        c.request(method, path, json.dumps(body).encode() if body is not None else None, headers)
        r = c.getresponse()
        data = json.loads(r.read())
        status = r.status
        c.close()
        return status, data

    def test_live_health_is_public_and_action_requires_auth(self):
        self.assertEqual(self.request("GET", "/health/live")[0], 200)
        self.assertEqual(self.request("GET", "/health/ready")[0], 200)
        self.assertEqual(self.request("POST", "/v1/actions", {"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-alice-001"}}, idem="no-auth")[0], 401)

    def test_http_decisions_and_empty_execute_body(self):
        status, denied = self.request("POST", "/v1/actions", {"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-bob-001"}}, "a" * 40, "denied")
        self.assertEqual(status, 403)
        self.assertEqual(denied["decision"], "DENY")

        status, pending = self.request("POST", "/v1/actions", {"task_id": "task-alice-001", "tool": "send_report", "arguments": {"artifact_id": "artifact-1", "destination_id": "internal-review-outbox"}}, "a" * 40, "pending")
        self.assertEqual(status, 202)
        self.assertEqual(pending["state"], "PENDING_APPROVAL")
        self.request("POST", f"/v1/approvals/{pending['approval_id']}/decision", {"decision": "approve"}, "r" * 40)
        status, done = self.request("POST", f"/v1/actions/{pending['action_id']}/execute", token="a" * 40)
        self.assertEqual(status, 200)
        self.assertEqual(done["state"], "SUCCEEDED")

    def test_audit_is_append_only_at_application_database_layer(self):
        self.gateway.create_action(self.gateway.authenticate("a" * 40), {"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-alice-001"}}, "audit-trigger")
        with self.assertRaises(Exception):
            self.gateway.db.execute("UPDATE audit SET event='altered'")
        with self.assertRaises(Exception):
            self.gateway.db.execute("DELETE FROM audit")

    def test_audit_api_requires_reviewer_and_scopes_events_by_tenant(self):
        alice = self.gateway.create_action(self.gateway.authenticate("a" * 40), {"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-alice-001"}}, "alice-audit")
        bob = self.gateway.create_action(self.gateway.authenticate("b" * 40), {"task_id": "task-bob-001", "tool": "read_document", "arguments": {"document_id": "report-bob-001"}}, "bob-audit")
        status, _ = self.request("GET", "/v1/audit/events", token="a" * 40)
        self.assertEqual(status, 403)
        status, payload = self.request("GET", "/v1/audit/events", token="r" * 40)
        self.assertEqual(status, 200)
        action_ids = {event["action_id"] for event in payload["items"]}
        self.assertIn(alice["action_id"], action_ids)
        self.assertNotIn(bob["action_id"], action_ids)


if __name__ == "__main__":
    unittest.main()
