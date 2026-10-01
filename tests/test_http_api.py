import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from gateway.app.main import Handler
from gateway.app.core import token_hash
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

    def test_agent_token_cannot_approve_and_pending_state_is_unchanged(self):
        pending = self.gateway.create_action(self.gateway.authenticate("a" * 40), {"task_id": "task-alice-001", "tool": "send_report", "arguments": {"artifact_id": "artifact-1", "destination_id": "internal-review-outbox"}}, "reviewer-only")
        status, body = self.request("POST", f"/v1/approvals/{pending['approval_id']}/decision", {"decision": "approve"}, "a" * 40)
        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "REVIEWER_REQUIRED")
        approval_state = self.gateway.db.execute("SELECT state FROM approvals WHERE id=?", (pending["approval_id"],)).fetchone()["state"]
        self.assertEqual(approval_state, "PENDING")
        self.assertFalse(any(path == "/internal/execute" for _, path, _ in self.gateway.calls))

    def test_revoked_agent_credential_cannot_execute_approved_action(self):
        pending = self.gateway.create_action(self.gateway.authenticate("a" * 40), {"task_id": "task-alice-001", "tool": "send_report", "arguments": {"artifact_id": "artifact-1", "destination_id": "internal-review-outbox"}}, "revoke-after-approve")
        self.request("POST", f"/v1/approvals/{pending['approval_id']}/decision", {"decision": "approve"}, "r" * 40)
        self.gateway.db.execute("UPDATE token_registry SET revoked=? WHERE token_hash=?", (1.0, token_hash("a" * 40)))
        status, _ = self.request("POST", f"/v1/actions/{pending['action_id']}/execute", token="a" * 40)
        self.assertEqual(status, 401)
        action = self.gateway.db.execute("SELECT state FROM actions WHERE id=?", (pending["action_id"],)).fetchone()
        self.assertEqual(action["state"], "APPROVED")
        self.assertFalse(any(path == "/internal/execute" for _, path, _ in self.gateway.calls))

    def test_missing_typed_and_extra_arguments_are_rejected_without_actions(self):
        invalid_bodies = (
            {"task_id": "task-alice-001", "tool": "read_document"},
            {"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": 42}},
            {"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-alice-001", "command": "run"}},
            {"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-alice-001"}, "role": "admin"},
        )
        for index, body in enumerate(invalid_bodies):
            status, _ = self.request("POST", "/v1/actions", body, "a" * 40, f"invalid-shape-{index}")
            self.assertEqual(status, 422)
        self.assertEqual(self.gateway.db.execute("SELECT COUNT(*) AS n FROM actions").fetchone()["n"], 0)
        self.assertFalse(any(path == "/internal/execute" for _, path, _ in self.gateway.calls))

    def test_action_budget_returns_http_429_without_an_extra_tool_call(self):
        self.gateway.policy["limits"]["actions_per_minute"] = 1
        body = {"task_id": "task-alice-001", "tool": "read_document", "arguments": {"document_id": "report-alice-001"}}
        status, first = self.request("POST", "/v1/actions", body, "a" * 40, "http-budget-first")
        self.assertEqual(status, 200)
        self.assertEqual(first["state"], "SUCCEEDED")
        status, limited = self.request("POST", "/v1/actions", body, "a" * 40, "http-budget-over")
        self.assertEqual(status, 429)
        self.assertEqual(limited["error"], "ACTION_RATE_LIMITED")
        self.assertEqual(self.gateway.db.execute("SELECT COUNT(*) AS n FROM actions").fetchone()["n"], 1)
        self.assertEqual(sum(1 for _, path, _ in self.gateway.calls if path == "/internal/execute"), 1)

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
