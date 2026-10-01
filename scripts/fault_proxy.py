"""Test-only proxy for controlled tool response-loss and restart experiments.

Run only on an isolated test Compose project. It forwards requests to the tool
service, commits the tool operation, then either drops or holds the response
to the Gateway. It never prints request headers or bodies.
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


UPSTREAM = os.environ.get("TOOL_UPSTREAM", "http://tool-sandbox:8001").rstrip("/")
MODE = os.environ.get("FAULT_MODE", "drop")
if MODE not in {"drop", "hold", "prehold"}:
    raise RuntimeError("FAULT_MODE must be drop, hold, or prehold")
entered = threading.Event()
release = threading.Event()
state_lock = threading.Lock()
forwarded = False


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def _json(self, status: int, data: dict) -> None:
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/fault/status":
            with state_lock:
                done = forwarded
            self._json(200, {"mode": MODE, "tool_operation_forwarded": done, "fault_gate_active": MODE in {"hold", "prehold"} and entered.is_set() and not release.is_set()})
            return
        if self.path == "/fault/wait":
            self._json(200 if entered.wait(180) else 504, {"tool_operation_forwarded": entered.is_set()})
            return
        self._forward()

    def do_POST(self):
        if self.path == "/fault/release":
            release.set()
            self._json(200, {"released": True})
            return
        self._forward()

    def _forward(self):
        global forwarded
        is_execute = self.path == "/internal/execute" and self.command == "POST"
        if is_execute and MODE == "prehold":
            entered.set()
            release.wait(180)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in {"host", "content-length", "connection"}}
        request = Request(UPSTREAM + self.path, data=body, method=self.command, headers=headers)
        try:
            with urlopen(request, timeout=10) as response:
                status, payload = response.status, response.read()
        except HTTPError as exc:
            status, payload = exc.code, exc.read()
        except (URLError, TimeoutError, OSError):
            self._json(503, {"error": "tool unavailable"})
            return

        if is_execute:
            with state_lock:
                forwarded = True
            if MODE == "hold":
                entered.set()
                release.wait(180)
            # Intentionally close without forwarding the already committed
            # response. A caller must reconcile by execution ID/receipt.
            self.close_connection = True
            self.connection.shutdown(2)
            self.connection.close()
            return

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("FAULT_PROXY_PORT", "8002"))), Handler).serve_forever()
