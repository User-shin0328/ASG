"""Local-only extensions; container mode always requires reviewer credentials."""
from __future__ import annotations
import threading
import uuid
from urllib.parse import urlparse, parse_qs
from dashboard.server import Handler
from security_agent.http_safety import BoundedHTTPServer


class SocDashboardHandler(Handler):
    generator = None
    lab = None
    generation_lock = threading.Lock()

    def valid_host(self):
        return self.headers.get("Host", "") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.valid_host():
            return self.respond(403, {"error": "LOOPBACK_HOST_REQUIRED"})
        if urlparse(self.path).path == "/api/context":
            return self.respond(200, {"mode": "local", "label": "로컬 검증 · DB 확인 중", "simulator": True})
        return super().do_GET()

    def do_POST(self):
        if not self.valid_host() or not self.mutation_allowed():
            return self.respond(403, {"error": "SAME_ORIGIN_REQUIRED"})
        if urlparse(self.path).path == '/api/db-demo':
            from scripts.traffic_generator import send_request
            body=self.body()
            if body is None or set(body)!={'scenario'} or body['scenario'] not in {'normal','sensitive','bulk','abnormal'}:
                return self.respond(422,{'error':'INVALID_SCENARIO'})
            arguments={'dataset_id':'operations','columns':['ticket_id','category','status'],'filters':{},'row_limit':25,
                'purpose':'월간 운영 지원 현황을 확인하기 위한 검증용 조회입니다.'}
            if body['scenario']=='sensitive':arguments.update(dataset_id='payroll',columns=['employee_id','salary','bank_account'])
            if body['scenario']=='bulk':arguments['row_limit']=2000
            if body['scenario']=='abnormal':arguments['columns']=['password','*']
            status,result=send_request(self.gateway_url+'/v1/db/requests','POST',self.generator._headers(self.generator.alice_token,str(uuid.uuid4())),arguments)
            return self.respond(200 if status<500 else 503,{'gateway_status':status,'request':result})
        if urlparse(self.path).path == "/api/generate":
            modes = {"normal": "run_normal_read", "cross-tenant": "run_cross_tenant_violation", "injection": "run_prompt_injection_inspection", "obfuscation": "run_unicode_obfuscation", "unapproved": "run_unapproved_report_submit", "audit-verify": "run_audit_verify"}
            mode = parse_qs(urlparse(self.path).query).get("mode", [""])[0]
            payload = self.body()
            if payload is None:
                return self.respond(400, {"error": "INVALID_JSON_OR_SIZE"})
            if mode != "custom" and mode not in modes:
                return self.respond(400, {"error": "UNKNOWN_MODE"})
            if mode == "custom" and (not isinstance(payload.get("text"), str) or not 1 <= len(payload["text"]) <= 8000):
                return self.respond(422, {"error": "TEXT_REQUIRED_1_TO_8000"})
            if not self.generation_lock.acquire(blocking=False):
                return self.respond(409, {"error": "SIMULATOR_BUSY"})
            try:
                result = self.generator.run_custom_prompt(payload["text"]) if mode == "custom" else getattr(self.generator, modes[mode])()
                return self.respond(200 if result["status"] < 500 else 503, result)
            finally:
                self.generation_lock.release()
        return super().do_POST()


def run_soc_dashboard(host="127.0.0.1", port=8501):
    BoundedHTTPServer((host, port), SocDashboardHandler).serve_forever()
