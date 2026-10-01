"""Safe, read-only network and container-boundary checks for the demo agent."""
from __future__ import annotations

import argparse
import os
import socket
import urllib.error
import urllib.request


def can_connect(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def require_blocked(host: str, port: int) -> None:
    if can_connect(host, port):
        raise SystemExit(f"Unexpectedly reachable: {host}:{port}")
    print(f"blocked={host}:{port}")


def agent_checks(tool_ip: str | None = None, postgres_ip: str | None = None, host_ips: list[str] | None = None) -> None:
    if not can_connect("gateway", 8000):
        raise SystemExit("Gateway is not reachable from the agent network")
    print("reachable=gateway:8000")
    for label, host, port in (("tool-sandbox", "tool-sandbox", 8001), ("postgres", "postgres", 5432)):
        try:
            addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
        except OSError:
            addresses = []
        if not addresses:
            print(f"dns_unresolved={label}:{port}")
        elif any(can_connect(address, port) for address in addresses):
            raise SystemExit(f"Unexpectedly reachable by service name: {label}:{port}")
        else:
            print(f"blocked_by_name={label}:{port}")

    for label, address, port in (("tool-sandbox", tool_ip, 8001), ("postgres", postgres_ip, 5432)):
        if address:
            if can_connect(address, port):
                raise SystemExit(f"Unexpectedly reachable by service IP: {label}:{port}")
            print(f"blocked_by_ip={label}:{port}")

    for host, port in (("host.docker.internal", 18501), ("1.1.1.1", 443)):
        require_blocked(host, port)
    for host_ip in host_ips or []:
        for port in (18501, 8000, 8001, 5432):
            if can_connect(host_ip, port):
                raise SystemExit(f"Unexpectedly reachable host interface on protected port {port}")
            print(f"blocked_host_interface_port={port}")

    routes = [line.split() for line in open("/proc/net/route", encoding="ascii").read().splitlines()[1:]]
    if any(route[1] == "00000000" for route in routes):
        raise SystemExit("Unexpected default route in agent container")
    print("default_route=absent")

    cap_eff = next(line.split()[1] for line in open("/proc/self/status", encoding="ascii") if line.startswith("CapEff:"))
    if int(cap_eff, 16) != 0:
        raise SystemExit("Agent container has effective Linux capabilities")
    if os.path.exists("/var/run/docker.sock"):
        raise SystemExit("Docker socket is mounted in the agent container")
    mount_targets = []
    for line in open("/proc/self/mountinfo", encoding="ascii"):
        fields = line.split()
        if len(fields) > 4:
            mount_targets.append(fields[4].replace("\\040", " "))
    forbidden_mounts = ("/host", "/mnt", "/workspace", "/run/secrets", "/var/lib/docker", "/var/run/docker.sock")
    if any(target == forbidden or target.startswith(forbidden + "/") for target in mount_targets for forbidden in forbidden_mounts):
        raise SystemExit("Agent container has a sensitive host-control or secret mount")
    try:
        with open("/agent-rootfs-probe", "x", encoding="ascii"):
            pass
    except OSError:
        pass
    else:
        os.unlink("/agent-rootfs-probe")
        raise SystemExit("Agent container root filesystem is writable")
    print("effective_capabilities=0 docker_socket=absent sensitive_mounts=absent root_filesystem=read-only")


def tool_auth_check() -> None:
    req = urllib.request.Request(
        "http://tool-sandbox:8001/internal/execute",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            print("unauthenticated_tool_request=401")
            return
        raise SystemExit(f"Unexpected tool authentication status: {exc.code}") from exc
    except OSError as exc:
        raise SystemExit("Tool sandbox is not reachable on its own network") from exc
    raise SystemExit("Unauthenticated tool request was accepted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool-auth", action="store_true")
    parser.add_argument("--tool-ip", default=os.environ.get("MATRIX_TOOL_IP"))
    parser.add_argument("--postgres-ip", default=os.environ.get("MATRIX_POSTGRES_IP"))
    parser.add_argument("--host-ips", default=os.environ.get("MATRIX_HOST_IPS", ""))
    args = parser.parse_args()
    if args.tool_auth:
        tool_auth_check()
    else:
        agent_checks(args.tool_ip, args.postgres_ip, [ip for ip in args.host_ips.split(",") if ip])


if __name__ == "__main__":
    main()
