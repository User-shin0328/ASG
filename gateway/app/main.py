from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from gateway.app.core import Gateway, GatewayError
from security_agent.http_safety import SafeHTTPHandler, BoundedHTTPServer, HTTPBodyError, read_json_body


def build_gateway():
    vals = {"agent-alice": os.environ.get("AGENT_ALICE_TOKEN", ""), "agent-bob": os.environ.get("AGENT_BOB_TOKEN", ""), "reviewer-demo": os.environ.get("REVIEWER_TOKEN", "")}
    if any(len(v) < 32 for v in vals.values()):
        raise RuntimeError("Agent and reviewer tokens must be generated secrets of at least 32 characters")
    password_file = os.environ.get("DATABASE_PASSWORD_FILE")
    if password_file:
        password = Path(password_file).read_text(encoding="utf-8").strip()
        if len(password) < 32:
            raise RuntimeError("PostgreSQL application secret is missing or too short")
        from psycopg.conninfo import make_conninfo

        database = make_conninfo(
            host=os.environ.get("DATABASE_HOST", "postgres"),
            port=os.environ.get("DATABASE_PORT", "5432"),
            dbname=os.environ.get("DATABASE_NAME", "gateway"),
            user=os.environ.get("DATABASE_USER", "gateway_app"),
            password=password,
            connect_timeout=5,
            application_name="ai-agent-security-gateway",
        )
    else:
        database = os.environ.get("DATABASE_PATH", "/data/gateway.sqlite3")
    return Gateway(database, vals, os.environ.get("TOOL_URL", "http://tool-sandbox:8001"), os.environ.get("TOOL_SERVICE_TOKEN", ""), os.environ.get("POLICY_FILE", "/app/config/policy.yaml"))


class Handler(SafeHTTPHandler):
    server_version = "ASG/2.0"
    gateway: Gateway

    def log_message(self, fmt, *args):
        return

    def send_json(self, status, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        return read_json_body(self, self.gateway.policy['limits']['request_bytes'])

    def principal(self):
        auth = self.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else None
        return self.gateway.authenticate(token)

    def route(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/health/live" and self.command == "GET":
            return 200, {"status": "live"}
        if path == "/health/ready" and self.command == "GET":
            return 200, self.gateway.ready()
        if path == "/" and self.command == "GET":
            return 200, {"service": "ASG (AI Agent Secure Gateway)", "openapi": "/openapi.json", "policy_version": self.gateway.policy["version"]}
        if path == "/openapi.json" and self.command == "GET":
            return 200, {"openapi": "3.1.0", "info": {"title": "ASG (AI Agent Secure Gateway)", "version": "0.1.0"}, "paths": {"/v1/actions": {"post": {"summary": "Create policy-checked action"}}, "/v1/inputs/inspect": {"post": {"summary": "Inspect untrusted text"}}}}
        p = self.principal()
        if path.startswith('/v1/db/'):
            service = self.gateway.db_access
            query = parse_qs(urlparse(self.path).query)
            if path == '/v1/db/recovery' and self.command=='GET':
                try:page=int(query.get('page',['1'])[0])
                except ValueError:raise GatewayError(422,'INVALID_PAGE','페이지 번호가 올바르지 않습니다.')
                return 200,service.recovery(p,page)
            if path == '/v1/db/requests' and self.command == 'POST':
                result = service.create(p,self.body(),self.headers.get('Idempotency-Key',''),self.client_address[0],self.headers.get('User-Agent',''))
                return (403 if result['decision']=='DENY' else 200 if result['decision']=='ALLOW' else 202),result
            if path == '/v1/db/requests' and self.command == 'GET':
                try: page=int(query.get('page',['1'])[0])
                except ValueError: raise GatewayError(422,'INVALID_PAGE','페이지 번호가 올바르지 않습니다.')
                return 200,service.listing(p,query.get('date',[None])[0],query.get('pending',['false'])[0]=='true',query.get('sort',['newest'])[0],page)
            if path == '/v1/db/overview' and self.command == 'GET':return 200,service.overview(p)
            if path == '/v1/db/status' and self.command == 'GET':return 200,service.status(p)
            if path == '/v1/db/grants' and self.command == 'GET':return 200,service.grants(p)
            if path == '/v1/db/budgets' and self.command == 'GET':return 200,service.budgets(p)
            revoke=re.fullmatch(r'/v1/db/grants/([a-zA-Z0-9-]+)/revoke',path)
            if revoke and self.command=='POST':
                body=self.body()
                if set(body)!={'reason'}:raise GatewayError(422,'INVALID_REQUEST','reason이 필요합니다.')
                return 200,service.revoke_grant(p,revoke.group(1),body['reason'])
            if path == '/v1/db/diagnostics' and self.command == 'POST':
                if self.body(): raise GatewayError(422,'INVALID_REQUEST','본문은 빈 객체여야 합니다.')
                return 200,service.diagnostics(p)
            match=re.fullmatch(r'/v1/db/requests/([a-zA-Z0-9-]+)(?:/(decision|execute|reconcile))?',path)
            if match:
                request_id,operation=match.groups()
                if not operation and self.command=='GET':return 200,service.detail(p,request_id)
                if operation=='decision' and self.command=='POST':
                    body=self.body()
                    if set(body) not in ({'decision','reason'},{'decision','reason','scope_grant'}):raise GatewayError(422,'INVALID_REQUEST','decision과 reason이 필요합니다.')
                    return 200,service.decide(p,request_id,body['decision'],body['reason'],body.get('scope_grant'))
                if operation=='execute' and self.command=='POST':
                    if self.body():raise GatewayError(422,'INVALID_REQUEST','본문은 빈 객체여야 합니다.')
                    return 200,service.execute(p,request_id)
                if operation=='reconcile' and self.command=='POST':
                    if self.body():raise GatewayError(422,'INVALID_REQUEST','본문은 빈 객체여야 합니다.')
                    return 200,service.reconcile(p,request_id)
            raise GatewayError(404,'NOT_FOUND','DB API를 찾을 수 없습니다.')
        if path == "/v1/actions" and self.command == "POST":
            idem = self.headers.get("Idempotency-Key", "")
            result = self.gateway.create_action(p, self.body(), idem)
            return (403 if result["decision"] == "DENY" else 202 if result["decision"] == "REQUIRE_APPROVAL" else 200), result
        if path == "/v1/inputs/inspect" and self.command == "POST":
            b = self.body()
            if set(b) != {"source", "text"} or not isinstance(b["source"], str):
                raise GatewayError(422, "INVALID_REQUEST", "source and text are required")
            return 200, self.gateway.inspect(p, b["source"], b["text"])
        m = re.fullmatch(r"/v1/actions/([A-Za-z0-9_.:-]+)", path)
        if m and self.command == "GET":
            return 200, self.gateway.action(p, m.group(1))
        m = re.fullmatch(r"/v1/actions/([A-Za-z0-9_.:-]+)/execute", path)
        if m and self.command == "POST":
            if int(self.headers.get("Content-Length", "0")) and self.body():
                raise GatewayError(422, "INVALID_REQUEST", "Execution request body must be empty")
            return 200, self.gateway.execute(p, m.group(1))
        if path == "/v1/approvals" and self.command == "GET":
            return 200, {"items": self.gateway.approvals(p)}
        m = re.fullmatch(r"/v1/approvals/([A-Za-z0-9_.:-]+)/decision", path)
        if m and self.command == "POST":
            b = self.body()
            if set(b) != {"decision"}:
                raise GatewayError(422, "INVALID_REQUEST", "decision is the only accepted field")
            return 200, self.gateway.decide(p, m.group(1), b["decision"])
        if path == "/v1/audit/events" and self.command == "GET":
            return 200, {"items": self.gateway.audit_events(p)}
        if path == "/v1/audit/verify" and self.command == "GET":
            return 200, self.gateway.verify_audit_chain(p)
        raise GatewayError(404, "NOT_FOUND", "Endpoint was not found")

    def do_GET(self):
        self.dispatch_request()

    def do_POST(self):
        self.dispatch_request()

    def dispatch_request(self):
        try:
            status, obj = self.route()
            if self.path.startswith("/v1/approvals") and status == 200:
                status = 200
            self.send_json(status, obj)
        except GatewayError as e:
            self.send_json(e.status, {"error": e.code, "message": e.message})
        except HTTPBodyError as error:
            self.body_error(error)
        except Exception:
            self.send_json(503, {"error": "INTERNAL_ERROR", "message": "Request could not be completed"})


def serve():
    Handler.gateway = build_gateway()
    host = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    port = int(os.environ.get("GATEWAY_PORT", "8000"))
    BoundedHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
