"""ASG-XDR Security Operations Center (SOC) Dashboard Server
Serves the dark-mode XDR dashboard, gathers live Windows telemetry,
and bridges to the ASG Traffic Generator and Gateway API.
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from scripts.traffic_generator import TrafficGenerator


ROOT_DIR = Path(__file__).resolve().parent
HTML_PATH = ROOT_DIR / "soc_dashboard.html"
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000")
DASHBOARD_PORT = int(os.environ.get("DASHBOARD_PORT", "8501"))


def get_live_host_telemetry() -> dict[str, Any]:
    """Collect real Windows host telemetry (Node, OS, CPU, RAM, IP)."""
    node = platform.node()
    os_name = f"{platform.system()} {platform.release()} {platform.version()}"
    arch = platform.machine()
    cpus = os.cpu_count() or 4

    # Memory via Windows API
    total_mb = 16384
    used_mb = 8192
    pct = 50.0
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong),
                ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong),
                ('ullAvailVirtual', ctypes.c_ulonglong),
                ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        total_mb = int(stat.ullTotalPhys // (1024 * 1024))
        used_mb = int((stat.ullTotalPhys - stat.ullAvailPhys) // (1024 * 1024))
        pct = round(stat.dwMemoryLoad, 1)
    except Exception:
        pass

    # IPv4 address
    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    return {
        "node": node,
        "os": os_name,
        "arch": arch,
        "cpus": cpus,
        "ram_total": total_mb,
        "ram_used": used_mb,
        "ram_pct": pct,
        "ip": ip,
    }


class SocDashboardHandler(BaseHTTPRequestHandler):
    server_version = "ASG-XDR-SOC/2.0"
    generator = TrafficGenerator(gateway_url=GATEWAY_URL)

    def log_message(self, fmt, *args):
        # Quiet logger for clean test output
        return

    def send_json(self, status: int, data: Any):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/" or path == "/index.html":
            if not HTML_PATH.exists():
                self.send_error(404, "Dashboard HTML not found")
                return
            content = HTML_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/host-info":
            return self.send_json(200, get_live_host_telemetry())

        if path == "/api/audit-events":
            import urllib.request
            try:
                req = urllib.request.Request(
                    f"{GATEWAY_URL}/v1/audit/events",
                    headers={"Authorization": f"Bearer {self.generator.reviewer_token}"}
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read())
                    return self.send_json(200, data)
            except Exception as e:
                # Return empty or fallback items
                return self.send_json(200, {"items": []})

        if path == "/api/audit-verify":
            res = self.generator.run_audit_verify()
            return self.send_json(200, res.get("result", {}))

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/api/generate":
            qs = parse_qs(parsed.query)
            mode = qs.get("mode", ["normal"])[0]

            if mode == "normal":
                return self.send_json(200, self.generator.run_normal_read())
            elif mode == "cross-tenant":
                return self.send_json(200, self.generator.run_cross_tenant_violation())
            elif mode == "injection":
                return self.send_json(200, self.generator.run_prompt_injection_inspection())
            elif mode == "obfuscation":
                return self.send_json(200, self.generator.run_unicode_obfuscation())
            elif mode == "unapproved":
                return self.send_json(200, self.generator.run_unapproved_report_submit())
            elif mode == "audit-verify":
                return self.send_json(200, self.generator.run_audit_verify())
            elif mode == "custom":
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length) if length else b"{}"
                try:
                    payload = json.loads(body)
                    text = payload.get("text", "")
                    return self.send_json(200, self.generator.run_custom_prompt(text))
                except Exception as exc:
                    return self.send_json(400, {"error": "INVALID_JSON", "message": str(exc)})

            return self.send_json(400, {"error": "UNKNOWN_MODE"})

        self.send_error(404, "Not Found")


def run_soc_dashboard(host: str = "127.0.0.1", port: int = DASHBOARD_PORT):
    server = ThreadingHTTPServer((host, port), SocDashboardHandler)
    print(f"[*] ASG-XDR SOC Dashboard running at http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_soc_dashboard()
