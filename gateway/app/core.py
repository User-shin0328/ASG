from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gateway.app.database import Database


DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "policy.yaml"
INSPECTION_PATTERNS = (
    "ignore previous instructions", "reveal the system prompt", "send all files", "ignore all prior instructions",
    "disregard the operating rules", "switch roles now", "constraints are obsolete", "ignore the assigned workflow",
    "administrator path", "only authority", "disclose the private rules", "confidential setup message",
    "hidden developer instructions", "internal system prompt", "list every secret", "private rules loaded at startup",
    "forward the complete set", "all reports from every account", "customer archive", "public upload folder",
    "export the full case database", "every attachment", "external mailbox", "outside recipient", "personal account",
    "other tenant", "south division", "bob's account", "another user's", "colleague's restricted",
    "skip the reviewer queue", "without asking the assigned reviewer", "approval for another document",
    "review step is optional", "after approval", "shell command to enumerate", "database directly and alter the audit",
    "container control socket", "unregistered network tool", "disable the safety checks", "internal execution endpoint",
    "active bearer token", "mounted secret files", "database password", "reviewer credential", "api key stored",
    "every credential available", "document footer", "image caption", "hidden note for automated readers",
    "spreadsheet comment directs", "ocr text", "기존 규칙을 무시하고", "승인 절차를 건너뛰고",
    "운영자 전용 자료를 모두 외부로", "비공개 계정의 문서를 제출해", "다른 테넌트의 문서를",
    "다른 사용자의", "시스템 프롬프트를 공개", "revela las instrucciones privadas", "transfere os ficheiros",
    "忽略当前限制", "les règles précédentes", "update the active rule", "erase the audit row",
    "replace the reviewer identity", "change the execution identifier", "edit the request arguments after approval",
)
INSPECTION_INTENT_RULES = (
    ("ROLE_REDEFINITION", re.compile(r"\b(?:behave as|act as|assume (?:the )?(?:role|persona)(?: of)?|pretend to be|you are now|become)\b.{0,80}\b(?:root|administrator|operator|unrestricted|system|developer|command interpreter|all.powerful)\b", re.I | re.S)),
    ("HIDDEN_INSTRUCTIONS", re.compile(r"\b(?:invisible|hidden|concealed|embedded|secret)\b.{0,70}\b(?:part|message|directions?|instructions?|content|payload|text)\b", re.I | re.S)),
    ("SECRET_DISCLOSURE", re.compile(r"\b(?:print|include|copy|reveal|disclose|put|expose|show|dump|list|return)\b.{0,80}\b(?:access string|authentication value|signing material|credential|token|secret|password|api key|system prompt|private instructions)\b", re.I | re.S)),
    ("POLICY_OVERRIDE", re.compile(r"(?:\b(?:review|safety|approval|authorization|restrictions?|controls?|checks?)\b.{0,60}\b(?:waived|optional|already handled|do not apply|does not apply|skip|bypass|ignore|not required|reject|deny|block)\b|\b(?:skip|bypass|waive|ignore)\b.{0,50}\b(?:review|safety|approval|authorization|restrictions?|controls?|checks?)\b)", re.I | re.S)),
    ("UNAUTHORIZED_TRANSFER", re.compile(r"\b(?:deliver|send|route|forward|use|change|redirect|email)\b.{0,80}\b(?:alternate destination|personal mailbox|outside recipient|different address|new endpoint|not listed|not on file|external recipient)\b", re.I | re.S)),
    ("CROSS_SCOPE_ACCESS", re.compile(r"\b(?:open|fetch|use|read|switch to|copy|retrieve|access)\b.{0,80}\b(?:coworker|finance group|other tenant|different team|another user|neighboring customer|another customer)\b", re.I | re.S)),
    ("TOOL_ESCALATION", re.compile(r"\b(?:use|launch|run|make|connect to|call|invoke)\b.{0,80}\b(?:shell command|database request|arbitrary web service|unregistered tool|tool that is not part|host command)\b", re.I | re.S)),
    ("APPROVAL_REPLAY", re.compile(r"(?:\b(?:reuse|apply|copy|use|treat)\b.{0,80}\b(?:previous sign.off|reviewer decision|approval|sign.off)\b.{0,40}\b(?:different|expired|already consumed|yesterday|another|old)\b|\b(?:already consumed|expired|from yesterday)\b.{0,50}\b(?:approval|review|sign.off)\b)", re.I | re.S)),
    ("INSTRUCTION_LAUNDERING", re.compile(r"\b(?:document|note|page|report|quoted|fetched)\b.{0,80}\b(?:obey|follow|perform|execute|do what it says|carry out)\b.{0,80}\b(?:directions?|instructions?|steps?|next steps|action|command|message)\b", re.I | re.S)),
    ("AUDIT_TAMPERING", re.compile(r"\b(?:remove|change|leave|rewrite|erase|delete|alter|edit)\b.{0,80}\b(?:decision record|history entry|review trail|recorded identity|denial event|audit|history|log)\b", re.I | re.S)),
)
ALLOWED_DECISIONS = {"ALLOW", "DENY", "REQUIRE_APPROVAL"}
DOCUMENTS = {
    "report-alice-001": {"owner": "alice", "tenant": "north", "path": "alice.txt"},
    "report-bob-001": {"owner": "bob", "tenant": "south", "path": "bob.txt"},
    "report-alice-attack": {"owner": "alice", "tenant": "north", "path": "injection.txt"},
}
TASKS = {
    "task-alice-001": {"principal": "agent-alice", "user": "alice", "tenant": "north", "documents": ["report-alice-001", "report-alice-attack"], "destinations": ["internal-review-outbox"]},
    "task-bob-001": {"principal": "agent-bob", "user": "bob", "tenant": "south", "documents": ["report-bob-001"], "destinations": ["internal-review-outbox"]},
}
PRINCIPALS = {
    "agent-alice": {"kind": "agent", "role": "report-submitter", "user": "alice", "tenant": "north", "task": "task-alice-001"},
    "agent-bob": {"kind": "agent", "role": "report-writer", "user": "bob", "tenant": "south", "task": "task-bob-001"},
    "reviewer-demo": {"kind": "reviewer", "role": "reviewer", "user": "reviewer", "tenant": "north"},
}


class GatewayError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def load_policy(path: str | Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    """Load strict JSON-syntax YAML (JSON is a YAML 1.2 subset) without extra dependencies."""
    try:
        policy = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Policy configuration is missing or invalid JSON-compatible YAML") from exc
    if not isinstance(policy, dict) or set(policy) != {"version", "default", "decisions", "tools", "destinations", "limits"}:
        raise RuntimeError("Policy configuration has missing or unknown top-level fields")
    if not isinstance(policy["version"], str) or not policy["version"] or policy["default"] != "DENY":
        raise RuntimeError("Policy version must be set and the default decision must be DENY")
    if not isinstance(policy["decisions"], list) or set(policy["decisions"]) != ALLOWED_DECISIONS:
        raise RuntimeError("Policy decisions must contain the supported decision set")
    if not isinstance(policy["tools"], dict) or not policy["tools"]:
        raise RuntimeError("Policy must register at least one tool")
    for name, spec in policy["tools"].items():
        if not isinstance(name, str) or not isinstance(spec, dict) or set(spec) - {"roles", "requires_assigned_resource", "requires_approval", "arguments"}:
            raise RuntimeError("Policy tool entry contains invalid fields")
        if not isinstance(spec.get("roles"), list) or not spec["roles"] or any(not isinstance(role, str) or not role for role in spec["roles"]):
            raise RuntimeError("Each policy tool must define one or more roles")
        if not isinstance(spec.get("arguments"), list) or not spec["arguments"] or any(not isinstance(arg, str) or not arg for arg in spec["arguments"]):
            raise RuntimeError("Each policy tool must define its exact argument fields")
        for flag in ("requires_assigned_resource", "requires_approval"):
            if flag in spec and not isinstance(spec[flag], bool):
                raise RuntimeError("Policy flags must be booleans")
    if not isinstance(policy["destinations"], list) or any(not isinstance(x, str) or not x for x in policy["destinations"]):
        raise RuntimeError("Policy destinations must be strings")
    limits = policy["limits"]
    required_limits = {"request_bytes", "argument_string_chars", "approval_seconds", "actions_per_minute", "pending_approvals_per_principal"}
    if not isinstance(limits, dict) or set(limits) != required_limits or any(type(v) is not int or v <= 0 for v in limits.values()):
        raise RuntimeError("Policy limits are missing or invalid")
    if not policy["tools"].get("send_report", {}).get("requires_approval", False):
        raise RuntimeError("send_report must require reviewer approval")
    return policy


def scan_untrusted_text(text: str) -> list[str]:
    low = text.casefold()
    hits = [pattern for pattern in INSPECTION_PATTERNS if pattern.casefold() in low]
    hits.extend(f"intent:{rule_id}" for rule_id, pattern in INSPECTION_INTENT_RULES if pattern.search(text))
    return list(dict.fromkeys(hits))


@dataclass(frozen=True)
class Principal:
    id: str
    kind: str
    role: str
    user: str
    tenant: str
    task: str | None = None


class Gateway:
    """PostgreSQL runtime gateway with a SQLite adapter for isolated tests."""

    def __init__(self, database: str = ":memory:", tokens: dict[str, str] | None = None, tool_url: str | None = None, tool_token: str | None = None, policy_path: str | Path = DEFAULT_POLICY_PATH):
        self.database = database
        self.policy = load_policy(policy_path)
        try:
            self.tool_timeout_seconds = float(os.environ.get("TOOL_REQUEST_TIMEOUT_SECONDS", "3"))
        except ValueError as exc:
            raise RuntimeError("Tool request timeout must be a number between 0 and 60 seconds") from exc
        if not 0 < self.tool_timeout_seconds <= 60:
            raise RuntimeError("Tool request timeout must be greater than 0 and no more than 60 seconds")
        self.db = Database(database)
        self.lock = threading.RLock()
        self.tokens = {token_hash(v): k for k, v in (tokens or {}).items()}
        self.tool_url = (tool_url or "").rstrip("/")
        self.tool_token = tool_token or ""
        if not self.db.is_postgres:
            self._schema()
        self._register_configured_tokens()

    def _schema(self) -> None:
        self.db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY, principal TEXT NOT NULL, task TEXT NOT NULL,
          tool TEXT NOT NULL, arguments TEXT NOT NULL, request_hash TEXT NOT NULL, idem_key TEXT NOT NULL,
          decision TEXT NOT NULL, state TEXT NOT NULL, reasons TEXT NOT NULL, policy_version TEXT NOT NULL,
          trace_id TEXT NOT NULL, execution_id TEXT, approval_id TEXT, created REAL NOT NULL,
          UNIQUE(principal, task, idem_key));
        CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, action_id TEXT NOT NULL UNIQUE REFERENCES actions(id),
          snapshot_hash TEXT NOT NULL, state TEXT NOT NULL, reviewer TEXT, expires REAL NOT NULL, used REAL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, trace_id TEXT NOT NULL,
          action_id TEXT, actor TEXT NOT NULL, event TEXT NOT NULL, details TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS inspections(id TEXT PRIMARY KEY, principal TEXT NOT NULL, source TEXT NOT NULL,
          verdict TEXT NOT NULL, reasons TEXT NOT NULL, scanner_version TEXT NOT NULL, content_hash TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS token_registry(token_hash TEXT PRIMARY KEY, principal TEXT NOT NULL, issued REAL NOT NULL, revoked REAL);
        CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'audit is append only'); END;
        CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'audit is append only'); END;
        """)
    def _register_configured_tokens(self) -> None:
        for hashed, principal in self.tokens.items():
            if self.db.is_postgres:
                self.db.execute("INSERT INTO token_registry(token_hash,principal,issued,revoked) VALUES(?,?,?,NULL) ON CONFLICT(token_hash) DO NOTHING", (hashed, principal, time.time()))
            else:
                self.db.execute("INSERT OR IGNORE INTO token_registry(token_hash,principal,issued,revoked) VALUES(?,?,?,NULL)", (hashed, principal, time.time()))

    def _policy_version(self) -> str:
        return self.policy["version"]

    def ready(self) -> dict[str, str]:
        try:
            with self.lock:
                self.db.execute("SELECT 1").fetchone()
            self._tool_request("GET", "/health/live")
            return {"status": "ready", "policy_version": self._policy_version()}
        except GatewayError:
            raise
        except Exception:
            raise GatewayError(503, "NOT_READY", "A required dependency is unavailable")

    def authenticate(self, token: str | None) -> Principal:
        principal_id = None
        if token:
            row = self.db.execute("SELECT principal FROM token_registry WHERE token_hash=? AND revoked IS NULL", (token_hash(token),)).fetchone()
            principal_id = row["principal"] if row else None
        data = PRINCIPALS.get(principal_id or "")
        if not data:
            raise GatewayError(401, "UNAUTHENTICATED", "A valid bearer token is required")
        return Principal(principal_id, data["kind"], data["role"], data["user"], data["tenant"], data.get("task"))

    def _audit(self, trace: str, action: str | None, actor: str, event: str, details: dict[str, Any]) -> None:
        # Never persist credentials or full document text in audit details.
        safe = {k: v for k, v in details.items() if k not in {"token", "content", "body", "authorization"}}
        self.db.execute("INSERT INTO audit(at,trace_id,action_id,actor,event,details) VALUES(?,?,?,?,?,?)",
                        (time.time(), trace, action, actor, event, json.dumps(safe, ensure_ascii=False)))

    def inspect(self, principal: Principal, source: str, text: str) -> dict[str, Any]:
        if principal.kind != "agent":
            raise GatewayError(403, "AGENT_REQUIRED", "Input inspection is available to agents")
        if not isinstance(text, str) or len(text) > 20000:
            raise GatewayError(422, "INVALID_INPUT", "text must be a string of at most 20000 characters")
        hits = scan_untrusted_text(text)
        verdict = "SUSPICIOUS" if hits else "CLEAR"
        inspection_id = str(uuid.uuid4())
        with self.lock:
            self.db.execute("INSERT INTO inspections VALUES(?,?,?,?,?,?,?,?)", (inspection_id, principal.id, source[:80], verdict, json.dumps(hits), "rules-v1", digest(text), time.time()))
            self._audit(str(uuid.uuid4()), None, principal.id, "INPUT_INSPECTED", {"inspection_id": inspection_id, "verdict": verdict, "source": source[:80], "content_hash": digest(text)})
        return {"inspection_id": inspection_id, "verdict": verdict, "reason_codes": ["PROMPT_INJECTION_PATTERN"] if hits else [], "scanner_version": "rules-v1", "content_hash": digest(text)}

    def _validate(self, p: Principal, task_id: Any, tool: Any, args: Any) -> tuple[dict[str, Any], list[str]]:
        if p.kind != "agent" or not p.task:
            raise GatewayError(403, "AGENT_REQUIRED", "This action requires an agent principal")
        if not isinstance(task_id, str) or task_id != p.task:
            raise GatewayError(403, "TASK_NOT_ASSIGNED", "Task is not assigned to this agent")
        if tool not in self.policy["tools"]:
            raise GatewayError(403, "TOOL_NOT_REGISTERED", "Tool is not registered")
        if not isinstance(args, dict):
            raise GatewayError(422, "INVALID_ARGUMENTS", "arguments must be an object")
        allowed_fields = set(self.policy["tools"][tool]["arguments"])
        if set(args) != allowed_fields:
            raise GatewayError(422, "INVALID_ARGUMENTS", "Missing or unknown argument fields")
        for k, v in args.items():
            if not isinstance(v, str) or not v or len(v) > (self.policy["limits"]["argument_string_chars"] if k == "content" else 100):
                raise GatewayError(422, "INVALID_ARGUMENTS", "Argument is empty, oversized, or has an invalid type")
        task = TASKS[task_id]
        if p.role not in self.policy["tools"][tool]["roles"]:
            return task, ["ROLE_FORBIDS_TOOL"]
        tool_policy = self.policy["tools"][tool]
        if tool_policy.get("requires_assigned_resource", False) and "document_id" in args:
            doc_id = args["document_id"]
            doc = DOCUMENTS.get(doc_id)
            if not doc:
                return task, ["RESOURCE_NOT_REGISTERED"]
            if doc_id not in task["documents"] or doc["owner"] != p.user or doc["tenant"] != p.tenant:
                return task, ["RESOURCE_OUT_OF_SCOPE"]
        if "destination_id" in args:
            if args["destination_id"] not in task["destinations"] or args["destination_id"] not in self.policy["destinations"]:
                return task, ["DESTINATION_NOT_REGISTERED"]
        if tool_policy.get("requires_assigned_resource", False) and "artifact_id" in args:
            if not self._artifact_in_scope(args["artifact_id"], p):
                return task, ["ARTIFACT_OUT_OF_SCOPE"]
        return task, []

    def _artifact_in_scope(self, artifact_id: str, p: Principal) -> bool:
        try:
            result = self._tool_request("GET", f"/internal/artifacts/{artifact_id}")
            return result.get("owner") == p.user and result.get("tenant") == p.tenant
        except GatewayError as e:
            if e.status == 404:
                return False
            raise

    def _tool_request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.tool_url:
            raise GatewayError(503, "TOOL_UNAVAILABLE", "Tool service is not configured")
        from urllib.error import HTTPError, URLError
        from urllib.request import Request, urlopen
        import json as _json
        data = _json.dumps(payload).encode() if payload is not None else None
        req = Request(self.tool_url + path, data=data, method=method, headers={"Authorization": f"Bearer {self.tool_token}", "Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=self.tool_timeout_seconds) as response:
                return _json.loads(response.read())
        except HTTPError as e:
            if e.code == 404:
                raise GatewayError(404, "RESOURCE_NOT_FOUND", "Registered resource was not found")
            raise GatewayError(503, "TOOL_UNAVAILABLE", "Tool service rejected or failed the request")
        except (URLError, TimeoutError, OSError):
            raise GatewayError(503, "TOOL_UNAVAILABLE", "Tool service is unavailable")

    def create_action(self, p: Principal, body: dict[str, Any], idem: str) -> dict[str, Any]:
        if not idem or len(idem) > 128:
            raise GatewayError(422, "INVALID_IDEMPOTENCY_KEY", "Idempotency-Key is required and limited to 128 characters")
        if set(body) != {"task_id", "tool", "arguments"}:
            raise GatewayError(422, "INVALID_REQUEST", "Request must contain task_id, tool, and arguments only")
        task, reasons = self._validate(p, body["task_id"], body["tool"], body["arguments"])
        req_hash = digest(body)
        # PostgreSQL advisory locking closes the cross-process check-then-insert race.
        idem_lock_key = "idempotency:" + canonical([p.id, body["task_id"], idem]).decode("utf-8")
        with self.lock, self.db.advisory_lock("action-budget:" + p.id), self.db.advisory_lock(idem_lock_key):
            prior = self.db.execute("SELECT * FROM actions WHERE principal=? AND task=? AND idem_key=?", (p.id, body["task_id"], idem)).fetchone()
            if prior:
                if prior["request_hash"] != req_hash:
                    raise GatewayError(409, "IDEMPOTENCY_CONFLICT", "Idempotency-Key was used with different content")
                return self.action(p, prior["id"])
            now = time.time()
            recent = self.db.execute("SELECT COUNT(*) AS count FROM actions WHERE principal=? AND created>=?", (p.id, now - 60)).fetchone()["count"]
            if recent >= self.policy["limits"]["actions_per_minute"]:
                raise GatewayError(429, "ACTION_RATE_LIMITED", "Action request budget exceeded")
            if body["tool"] == "send_report" and not reasons:
                pending = self.db.execute(
                    "SELECT COUNT(*) AS count FROM approvals a JOIN actions x ON x.id=a.action_id "
                    "WHERE x.principal=? AND a.state IN ('PENDING','APPROVED') AND a.expires>?",
                    (p.id, now),
                ).fetchone()["count"]
                if pending >= self.policy["limits"]["pending_approvals_per_principal"]:
                    raise GatewayError(429, "PENDING_APPROVAL_LIMIT", "Pending approval budget exceeded")
            aid, trace, eid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
            decision = "DENY" if reasons else ("REQUIRE_APPROVAL" if self.policy["tools"][body["tool"]].get("requires_approval", False) else "ALLOW")
            state = "DENIED" if reasons else ("PENDING_APPROVAL" if decision == "REQUIRE_APPROVAL" else "READY")
            approval_id = str(uuid.uuid4()) if decision == "REQUIRE_APPROVAL" else None
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.db.execute("INSERT INTO actions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (aid, p.id, body["task_id"], body["tool"], json.dumps(body["arguments"], ensure_ascii=False), req_hash, idem, decision, state, json.dumps(reasons), self._policy_version(), trace, eid, approval_id, now))
                if approval_id:
                    snap = self._approval_snapshot(p, body["task_id"], body["tool"], body["arguments"])
                    self.db.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?)", (approval_id, aid, digest(snap), "PENDING", None, time.time() + self.policy["limits"]["approval_seconds"], None))
                self._audit(trace, aid, p.id, "ACTION_CREATED", {"tool": body["tool"], "decision": decision, "reason_codes": reasons, "arguments_hash": digest(body["arguments"]), "policy_version": self._policy_version()})
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
            row = self.db.execute("SELECT * FROM actions WHERE id=?", (aid,)).fetchone()
            if decision == "ALLOW":
                return self.execute(p, aid)
            return self._action_json(row)

    def _approval_snapshot(self, p: Principal, task_id: str, tool: str, args: dict[str, str]) -> dict[str, Any]:
        return {"principal": p.id, "user": p.user, "tenant": p.tenant, "task_id": task_id, "tool": tool,
                "arguments": args, "policy_version": self._policy_version(), "artifact_hash": self._tool_request("GET", f"/internal/artifacts/{args['artifact_id']}")["content_hash"]}

    def execute(self, p: Principal, action_id: str) -> dict[str, Any]:
        with self.lock:
            row = self.db.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
            if not row or row["principal"] != p.id:
                raise GatewayError(404, "ACTION_NOT_FOUND", "Action was not found")
            if row["state"] == "SUCCEEDED":
                result = self._tool_request("GET", f"/internal/executions/{row['execution_id']}")
                return self._action_json(row, result)
            if row["decision"] == "DENY" or row["state"] not in {"READY", "APPROVED"}:
                raise GatewayError(409, "ACTION_NOT_EXECUTABLE", "Action is not approved and ready to execute")
            body = {"task_id": row["task"], "tool": row["tool"], "arguments": json.loads(row["arguments"])}
            _, reasons = self._validate(p, body["task_id"], body["tool"], body["arguments"])
            if reasons:
                self.db.execute("UPDATE actions SET state='DENIED',decision='DENY',reasons=? WHERE id=?", (json.dumps(reasons), action_id))
                raise GatewayError(403, "POLICY_RECHECK_DENIED", "Current policy no longer permits this action")
            self.db.execute("BEGIN IMMEDIATE")
            try:
                if row["approval_id"]:
                    lock_clause = " FOR UPDATE" if self.db.is_postgres else ""
                    approval = self.db.execute(f"SELECT * FROM approvals WHERE id=?{lock_clause}", (row["approval_id"],)).fetchone()
                    if not approval or approval["state"] != "APPROVED" or approval["expires"] < time.time() or approval["used"] is not None:
                        raise GatewayError(403, "APPROVAL_INVALID", "Approval is missing, expired, or already used")
                    snap = self._approval_snapshot(p, row["task"], row["tool"], json.loads(row["arguments"]))
                    if digest(snap) != approval["snapshot_hash"]:
                        raise GatewayError(403, "APPROVAL_SNAPSHOT_CHANGED", "Approved content or policy changed")
                    changed = self.db.execute("UPDATE approvals SET state='CONSUMED',used=? WHERE id=? AND state='APPROVED' AND used IS NULL", (time.time(), approval["id"])).rowcount
                    if changed != 1:
                        raise GatewayError(409, "APPROVAL_ALREADY_USED", "Approval was already consumed")
                self.db.execute("UPDATE actions SET state='EXECUTING' WHERE id=?", (action_id,))
                self._audit(row["trace_id"], action_id, p.id, "EXECUTION_STARTED", {"execution_id": row["execution_id"]})
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
            try:
                result = self._tool_request("POST", "/internal/execute", {"execution_id": row["execution_id"], "action_id": action_id, "principal": p.id, "user": p.user, "tenant": p.tenant, "task_id": row["task"], "tool": row["tool"], "arguments": json.loads(row["arguments"]), "request_hash": row["request_hash"]})
            except GatewayError:
                self.db.execute("UPDATE actions SET state='UNKNOWN' WHERE id=?", (action_id,))
                raise
            self.db.execute("UPDATE actions SET state='SUCCEEDED' WHERE id=?", (action_id,))
            self._audit(row["trace_id"], action_id, p.id, "EXECUTION_SUCCEEDED", {"execution_id": row["execution_id"], "receipt_id": result.get("receipt_id")})
            return self._action_json(self.db.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone(), result)

    def _action_json(self, row, result: dict[str, Any] | None = None) -> dict[str, Any]:
        approval = self.db.execute("SELECT state,expires FROM approvals WHERE id=?", (row["approval_id"],)).fetchone() if row["approval_id"] else None
        return {"action_id": row["id"], "decision": row["decision"], "state": row["state"], "reason_codes": json.loads(row["reasons"]), "approval_id": row["approval_id"], "approval_state": approval["state"] if approval else None, "execution_id": row["execution_id"], "trace_id": row["trace_id"], "policy_version": row["policy_version"], "result": result}

    def action(self, p: Principal, action_id: str) -> dict[str, Any]:
        with self.lock:
            row = self.db.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
        if p.kind == "agent":
            if not row or row["principal"] != p.id:
                raise GatewayError(404, "ACTION_NOT_FOUND", "Action was not found")
        elif p.kind != "reviewer":
            raise GatewayError(403, "FORBIDDEN", "Insufficient permission")
        if not row:
            raise GatewayError(404, "ACTION_NOT_FOUND", "Action was not found")
        if p.kind == "reviewer" and TASKS[row["task"]]["tenant"] != p.tenant:
            raise GatewayError(404, "ACTION_NOT_FOUND", "Action was not found")
        result = None
        if row["state"] in {"SUCCEEDED", "UNKNOWN", "EXECUTING"}:
            try:
                result = self._tool_request("GET", f"/internal/executions/{row['execution_id']}")
                if row["state"] != "SUCCEEDED":
                    with self.lock:
                        self.db.execute("UPDATE actions SET state='SUCCEEDED' WHERE id=?", (row["id"],))
                        self._audit(row["trace_id"], row["id"], p.id, "EXECUTION_RECOVERED", {"execution_id": row["execution_id"], "receipt_id": result.get("receipt_id")})
                        row = self.db.execute("SELECT * FROM actions WHERE id=?", (row["id"],)).fetchone()
            except GatewayError:
                result = None
                if row["state"] == "EXECUTING":
                    with self.lock:
                        self.db.execute("UPDATE actions SET state='UNKNOWN' WHERE id=?", (row["id"],))
                        self._audit(row["trace_id"], row["id"], p.id, "EXECUTION_STATE_UNKNOWN", {"execution_id": row["execution_id"]})
                        row = self.db.execute("SELECT * FROM actions WHERE id=?", (row["id"],)).fetchone()
        return self._action_json(row, result)

    def approvals(self, p: Principal) -> list[dict[str, Any]]:
        if p.kind != "reviewer":
            raise GatewayError(403, "REVIEWER_REQUIRED", "Reviewer credentials are required")
        rows = self.db.execute("SELECT a.id,a.action_id,a.expires,x.principal,x.task,x.tool,x.arguments,x.trace_id FROM approvals a JOIN actions x ON x.id=a.action_id WHERE a.state='PENDING' ORDER BY x.created").fetchall()
        items = []
        for r in rows:
            args = json.loads(r["arguments"])
            item = {"approval_id": r["id"], "action_id": r["action_id"], "expires_at": r["expires"], "principal": r["principal"], "task_id": r["task"], "tool": r["tool"], "arguments": args, "trace_id": r["trace_id"]}
            if r["tool"] == "send_report":
                artifact = self._tool_request("GET", f"/internal/artifacts/{args['artifact_id']}")
                item["review_snapshot"] = {"content": artifact["content"], "content_hash": artifact["content_hash"], "destination_id": args["destination_id"]}
            items.append(item)
        return items

    def decide(self, p: Principal, approval_id: str, decision: str) -> dict[str, Any]:
        if p.kind != "reviewer":
            raise GatewayError(403, "REVIEWER_REQUIRED", "Reviewer credentials are required")
        if decision not in {"approve", "reject"}:
            raise GatewayError(422, "INVALID_DECISION", "decision must be approve or reject")
        with self.lock:
            row = self.db.execute("SELECT a.*,x.trace_id FROM approvals a JOIN actions x ON x.id=a.action_id WHERE a.id=?", (approval_id,)).fetchone()
            if not row or row["state"] != "PENDING" or row["expires"] < time.time():
                raise GatewayError(409, "APPROVAL_NOT_PENDING", "Approval is missing, expired, or already decided")
            action = self.db.execute("SELECT * FROM actions WHERE id=?", (row["action_id"],)).fetchone()
            task = TASKS[action["task"]]
            if p.tenant != task["tenant"]:
                raise GatewayError(403, "REVIEWER_OUT_OF_SCOPE", "Reviewer cannot decide for this tenant")
            state = "APPROVED" if decision == "approve" else "REJECTED"
            self.db.execute("BEGIN IMMEDIATE")
            try:
                changed = self.db.execute("UPDATE approvals SET state=?,reviewer=? WHERE id=? AND state='PENDING'", (state, p.id, approval_id)).rowcount
                if changed != 1:
                    raise GatewayError(409, "APPROVAL_NOT_PENDING", "Approval was already decided")
                self.db.execute("UPDATE actions SET state=? WHERE id=?", ("APPROVED" if decision == "approve" else "REJECTED", action["id"]))
                self._audit(row["trace_id"], action["id"], p.id, "APPROVAL_" + state, {"approval_id": approval_id})
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
            return {"approval_id": approval_id, "action_id": action["id"], "state": state}

    def audit_events(self, p: Principal) -> list[dict[str, Any]]:
        if p.kind != "reviewer":
            raise GatewayError(403, "AUDITOR_REQUIRED", "Reviewer credentials are required")
        task_ids = [task_id for task_id, task in TASKS.items() if task["tenant"] == p.tenant]
        principal_ids = [principal_id for principal_id, principal in PRINCIPALS.items() if principal["tenant"] == p.tenant]
        task_marks = ",".join("?" for _ in task_ids) or "NULL"
        principal_marks = ",".join("?" for _ in principal_ids) or "NULL"
        sql = f"SELECT e.* FROM audit e LEFT JOIN actions x ON x.id=e.action_id WHERE x.task IN ({task_marks}) OR (e.action_id IS NULL AND e.actor IN ({principal_marks})) ORDER BY e.id DESC LIMIT 200"
        rows = self.db.execute(sql, [*task_ids, *principal_ids]).fetchall()
        return [dict(r) | {"details": json.loads(r["details"])} for r in rows]
