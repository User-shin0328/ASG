"""Loopback-only ASG lab and packaged Windows entry point."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class LoopbackHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = False

    def server_bind(self):
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def configure_packaged_loopback_http():
    """Avoid unused HTTPS/OpenSSL initialization in the offline, loopback-only EXE.

    The bundled OpenSSL build cannot initialize from a Korean extraction path.
    No TLS is required by this local lab. Remote hosts and redirects are rejected.
    Compose keeps Python's ordinary transport and is unaffected.
    """
    import urllib.request
    from urllib.error import URLError
    from urllib.parse import urlparse

    class LoopbackHandler(urllib.request.HTTPHandler):
        def http_open(self, request):
            if urlparse(request.full_url).hostname not in {'127.0.0.1', 'localhost', '::1'}:
                raise URLError('The packaged local lab only connects to loopback hosts')
            return super().http_open(request)

    opener = urllib.request.OpenerDirector()
    for handler in (LoopbackHandler(), urllib.request.HTTPDefaultErrorHandler(),
                    urllib.request.HTTPErrorProcessor(), urllib.request.UnknownHandler()):
        opener.add_handler(handler)
    urllib.request.install_opener(opener)


class LocalLab:
    def __init__(self, data_dir: Path, gateway_port=0, tool_port=0, dashboard_port=18511):
        self.data_dir = Path(data_dir).resolve()
        self.ports = (gateway_port, tool_port, dashboard_port)
        self.servers, self.threads = [], []
        self.gateway = None

    def start(self):
        from gateway.app.core import Gateway
        from gateway.app.main import Handler as GatewayHandler
        from tool_sandbox import app as sandbox
        from dashboard.soc_dashboard import SocDashboardHandler
        from scripts.traffic_generator import TrafficGenerator
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = open(self.data_dir / "session.lock", "a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.lock_file.seek(0)
                self.lock_file.write(b"0")
                self.lock_file.flush()
                self.lock_file.seek(0)
                msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock_file.close()
            raise RuntimeError("This data folder is already in use by ASG.") from None
        names={'agent-alice':'ASG_LAB_ALICE_TOKEN','agent-bob':'ASG_LAB_BOB_TOKEN','reviewer-demo':'ASG_LAB_REVIEWER_TOKEN','tool':'ASG_LAB_TOOL_TOKEN'}
        self.tokens={name:os.environ.get(variable) or secrets.token_urlsafe(36) for name,variable in names.items()}
        if any(len(token)<32 for token in self.tokens.values()) or len(set(self.tokens.values()))!=4:
            self.lock_file.close()
            raise RuntimeError('ASG_LAB tokens must be distinct secrets of at least 32 characters.')
        gp, tp, dp = self.ports
        sandbox.TOKEN = self.tokens["tool"]
        sandbox.DATABASE = str(self.data_dir / "tools.sqlite3")
        try:
            for port, handler in ((tp, sandbox.Handler), (gp, GatewayHandler), (dp, SocDashboardHandler)):
                self.servers.append(LoopbackHTTPServer(("127.0.0.1", port), handler))
            actual_tp, actual_gp, actual_dp = [s.server_port for s in self.servers]
            self.gateway_url = f"http://127.0.0.1:{actual_gp}"
            self.url = f"http://127.0.0.1:{actual_dp}"
            tool_url = f"http://127.0.0.1:{actual_tp}"
            self.gateway = Gateway(str(self.data_dir / "gateway.sqlite3"), {k: v for k, v in self.tokens.items() if k != "tool"}, tool_url, self.tokens["tool"])
            GatewayHandler.gateway = self.gateway
            SocDashboardHandler.generator = TrafficGenerator(self.gateway_url, self.tokens["agent-alice"], self.tokens["agent-bob"], self.tokens["reviewer-demo"])
            SocDashboardHandler.gateway_url = self.gateway_url
            SocDashboardHandler.tool_url = tool_url
            SocDashboardHandler.lab = self
            for server in self.servers:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                self.threads.append(thread)
            for base, health in ((tool_url, "/health/live"), (self.gateway_url, "/health/ready"), (self.url, "/health/ready")):
                with urlopen(base + health, timeout=5) as response:
                    if response.status != 200:
                        raise RuntimeError("A service is not ready")
            (self.data_dir / "session.json").write_text(json.dumps({"pid": os.getpid(), "dashboard": self.url, "gateway": self.gateway_url, "tool": tool_url, "started": time.time()}, indent=2), encoding="utf-8")
            return self
        except BaseException:
            self.stop()
            raise

    def stop(self):
        for index, server in enumerate(self.servers):
            if index < len(self.threads) and self.threads[index].is_alive():
                server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=3)
        self.servers.clear()
        self.threads.clear()
        if self.gateway:
            self.gateway.db.close()
            self.gateway = None
        if hasattr(self, "lock_file") and not self.lock_file.closed:
            self.lock_file.close()


def main():
    if getattr(sys, 'frozen', False):
        configure_packaged_loopback_http()
    parser = argparse.ArgumentParser(description="ASG local test environment")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ASG" / "lab")
    parser.add_argument("--gateway-port", type=int, default=0)
    parser.add_argument("--tool-port", type=int, default=0)
    parser.add_argument("--dashboard-port", type=int, default=18511)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--smoke-seconds", type=float, default=0)
    args = parser.parse_args()
    if any(p < 0 or p > 65535 for p in (args.gateway_port, args.tool_port, args.dashboard_port)) or args.smoke_seconds < 0:
        parser.error("Ports must be 0..65535 and smoke duration must be nonnegative")
    lab = LocalLab(args.data_dir, args.gateway_port, args.tool_port, args.dashboard_port)
    try:
        lab.start()
        print(f"ASG READY {lab.url}", flush=True)
        print(f"Local SQLite lab | Data: {lab.data_dir}", flush=True)
        print("Close this window or press Ctrl+C to stop all three services.", flush=True)
        if not args.no_browser:
            webbrowser.open(lab.url)
        if args.smoke_seconds:
            time.sleep(args.smoke_seconds)
        else:
            while True:
                time.sleep(.5)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"ASG START FAILED: {exc}", file=sys.stderr, flush=True)
        if not args.no_browser and os.name == "nt":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(exc), "ASG start failed", 0x10)
        return 1
    finally:
        lab.stop()


if __name__ == "__main__":
    raise SystemExit(main())
