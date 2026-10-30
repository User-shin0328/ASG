"""ASG (AI Agent Secure Gateway) - All-in-One Local Testbed Launcher
Spins up Tool Sandbox (8001), Gateway (8000), and SOC Dashboard (8501) in a single run.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

# Safe encoding for Windows console (cp949 / utf-8)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Default test tokens
ALICE_TOKEN = os.environ.get("AGENT_ALICE_TOKEN", "alice-demo-token-" + "x" * 24)
BOB_TOKEN = os.environ.get("AGENT_BOB_TOKEN", "bob-demo-token---" + "x" * 24)
REVIEWER_TOKEN = os.environ.get("REVIEWER_TOKEN", "reviewer-demo-tok" + "x" * 24)
TOOL_TOKEN = os.environ.get("TOOL_SERVICE_TOKEN", "tool-service-tok-" + "x" * 24)

# Export to environment for child modules
os.environ["AGENT_ALICE_TOKEN"] = ALICE_TOKEN
os.environ["AGENT_BOB_TOKEN"] = BOB_TOKEN
os.environ["REVIEWER_TOKEN"] = REVIEWER_TOKEN
os.environ["TOOL_SERVICE_TOKEN"] = TOOL_TOKEN
os.environ["GATEWAY_URL"] = "http://127.0.0.1:8000"
os.environ["TOOL_URL"] = "http://127.0.0.1:8001"


def run_tool_sandbox():
    import tool_sandbox.app as sandbox_mod
    sandbox_mod.TOKEN = TOOL_TOKEN
    server = ThreadingHTTPServer(("127.0.0.1", 8001), sandbox_mod.Handler)
    server.serve_forever()


def run_gateway():
    from gateway.app.core import Gateway
    import gateway.app.main as gw_main

    vals = {
        "agent-alice": ALICE_TOKEN,
        "agent-bob": BOB_TOKEN,
        "reviewer-demo": REVIEWER_TOKEN,
    }
    gw_main.Handler.gateway = Gateway(
        database=":memory:",
        tokens=vals,
        tool_url="http://127.0.0.1:8001",
        tool_token=TOOL_TOKEN,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 8000), gw_main.Handler)
    server.serve_forever()


def run_dashboard():
    from dashboard.soc_dashboard import run_soc_dashboard
    run_soc_dashboard(host="127.0.0.1", port=8501)


def main():
    print("=" * 70)
    print("  [ASG] AI Agent Secure Gateway - 로컬 통합 테스트베드")
    print("=" * 70)
    print("[1/3] 도구 샌드박스 (Tool Sandbox) 시작 중... (http://127.0.0.1:8001)")
    t_sandbox = threading.Thread(target=run_tool_sandbox, daemon=True)
    t_sandbox.start()

    time.sleep(0.5)

    print("[2/3] ASG 보안 게이트웨이 (Gateway Core) 시작 중... (http://127.0.0.1:8000)")
    t_gw = threading.Thread(target=run_gateway, daemon=True)
    t_gw.start()

    time.sleep(0.5)

    print("[3/3] ASG-XDR SOC 대시보드 & 공격 발생기 시작 중... (http://127.0.0.1:8501)")
    print("\n[+] 모든 보안 서비스가 정상 기동되었습니다!")
    print("    - 대시보드 URL : http://127.0.0.1:8501/")
    print("    - 게이트웨이 API: http://127.0.0.1:8000/")
    print("    - 도구 샌드박스 : http://127.0.0.1:8001/")
    print("\n[*] 기본 브라우저를 자동으로 실행합니다...")

    try:
        webbrowser.open("http://127.0.0.1:8501/")
    except Exception:
        pass

    print("[*] 종료하려면 터미널에서 Ctrl + C 를 누르세요.\n")
    try:
        run_dashboard()
    except KeyboardInterrupt:
        print("\n[*] ASG 테스트베드를 안전하게 종료합니다.")


if __name__ == "__main__":
    main()
