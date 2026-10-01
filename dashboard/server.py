from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith(("/v1/", "/health/")):
            self.proxy()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/v1/"):
            self.proxy()
        else:
            self.send_error(404)

    def proxy(self):
        base = os.environ.get("GATEWAY_URL", "http://gateway:8000")
        length = int(self.headers.get("Content-Length", "0"))
        if length > 24000:
            return self.send_error(413)
        raw = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() in {"authorization", "content-type", "idempotency-key"}}
        req = Request(base.rstrip("/") + self.path, data=raw, headers=headers, method=self.command)
        try:
            with urlopen(req, timeout=5) as response:
                payload, status = response.read(), response.status
        except HTTPError as e:
            payload, status = e.read(), e.code
        except URLError:
            payload, status = b'{"error":"GATEWAY_UNAVAILABLE"}', 503
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("DASHBOARD_PORT", "8501"))), Handler).serve_forever()
