"""Shared static UI and authenticated Gateway proxy for local and Compose modes."""
from pathlib import Path
import json
import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from security_agent.http_safety import SafeHTTPHandler, BoundedHTTPServer, read_json_body

ROOT = Path(__file__).resolve().parent
STATIC = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"), "/soc_dashboard.html": ("index.html", "text/html"), "/app.css": ("app.css", "text/css"), "/app.js": ("app.js", "text/javascript")}
for route in ('/approvals','/audit','/tests'):
    STATIC[route]=('index.html','text/html')


class Handler(SafeHTTPHandler):
    gateway_url = None

    def log_message(self, fmt, *args):
        pass

    def respond(self, status, content, mime="application/json"):
        raw = content if isinstance(content, bytes) else json.dumps(content, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        return read_json_body(self, 24000)

    def mutation_allowed(self):
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        return self.headers.get("X-ASG-Request") == "1" and (not origin or origin in {"http://" + host, "https://" + host})

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/context":
            return self.respond(200, {"mode": "container", "label": "컨테이너 · 인증 후 확인", "simulator": False})
        if path in STATIC:
            filename, mime = STATIC[path]
            return self.respond(200, (ROOT / filename).read_bytes(), mime)
        if path.startswith(("/v1/", "/health/")):
            return self.proxy()
        return self.respond(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        if not self.mutation_allowed():
            return self.respond(403, {"error": "SAME_ORIGIN_REQUIRED"})
        if urlparse(self.path).path.startswith("/v1/"):
            return self.proxy()
        return self.respond(404, {"error": "NOT_FOUND"})

    def proxy(self):
        base = self.gateway_url or os.environ.get("GATEWAY_URL", "http://gateway:8000")
        raw = None
        if self.command == "POST":
            body = self.body()
            if body is None:
                return self.respond(400, {"error": "INVALID_JSON_OR_SIZE"})
            raw = json.dumps(body).encode()
        headers = {k: v for k, v in self.headers.items() if k.lower() in {"authorization", "content-type", "idempotency-key"}}
        if getattr(self, "generator", None) and not any(k.lower() == "authorization" for k in headers):
            headers["Authorization"] = "Bearer " + self.generator.reviewer_token
        req = Request(base.rstrip("/") + self.path, data=raw, headers=headers, method=self.command)
        try:
            with urlopen(req, timeout=15) as response:
                payload, status = response.read(), response.status
        except HTTPError as exc:
            payload, status = exc.read(), exc.code
        except (URLError, TimeoutError, OSError):
            payload, status = b'{"error":"GATEWAY_UNAVAILABLE"}', 503
        self.respond(status, payload)


if __name__ == "__main__":
    BoundedHTTPServer(("0.0.0.0", int(os.environ.get("DASHBOARD_PORT", "8501"))), Handler).serve_forever()
