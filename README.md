# ASG: AI Agent Secure Gateway
> **Next-Generation Zero Trust Security Gateway & XDR Monitoring Platform for Autonomous AI Agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-blue.svg)](compose.yaml)
[![Tests Passing](https://img.shields.io/badge/Tests-74%2F74%20Passing-success.svg)](tests/)
[![Security: Zero Trust](https://img.shields.io/badge/Security-Zero%20Trust%20Enforced-orange.svg)](docs/threat-model.md)

---

## 📌 Overview

**ASG (AI Agent Secure Gateway)** is a specialized, defense-in-depth security gateway that intercepts and enforces policy controls on autonomous AI agents before they can interact with enterprise databases, files, APIs, and external tools.

Unlike standard chatbots that only generate text, **agentic AI workflows possess "hands and tools"** capable of querying databases, altering records, or sending emails. When subjected to **Indirect Prompt Injection**, an attacker can trick an agent into exfiltrating confidential corporate records or dropping critical databases.

**ASG acts as the single chokepoint (inline gatekeeper) between AI Agent runtimes and protected enterprise resources:**
- Never trusts the agent, model inferences, tool arguments, or document content (**Zero Trust**).
- Prevents identity spoofing by binding requests to **server-owned principals** derived from SHA-256 token hashes.
- Mandates **Human-in-the-Loop (HITL)** approval with cryptographic snapshot binding for high-risk side effects (e.g., report transmissions).
- Employs **multi-tier prompt injection guardrails** (Unicode NFKC normalization, regex heuristics, local n-gram Bernoulli classifier, and context-aware LLM guards).
- Enforces append-only, tamper-proof audit trails with **Merkle Hash Chaining**.

---

## 🚀 Key Features

| Capability | Description |
|---|---|
| **ASG-XDR SOC Dashboard** | High-performance, dark-themed security operations center UI at `http://127.0.0.1:8501/` with real-time Windows host telemetry (CPU, RAM, OS, IPv4), threat case management, and live intercept logs. |
| **Interactive Attack Generator** | Built-in simulator with 7 preset attack scenarios (normal summary, cross-tenant trespass, prompt injection, zero-width obfuscation, unapproved execution, Merkle verify) and real-time custom prompt injection testing. |
| **Server-Owned Principals** | Clients only supply opaque bearer tokens. ASG strictly injects `principal`, `role`, `task_id`, and `tenant` server-side, defeating identity spoofing. |
| **Cryptographic HITL Snapshots** | Dangerous actions remain `PENDING_APPROVAL` until signed off by a human reviewer. Approvals bind to `SHA-256(principal + task + args + artifact_hash + policy_version)` and are single-use with a 15-minute TTL. |
| **PostgreSQL Advisory Locks** | Eliminates race conditions and duplicate executions via distributed advisory locks and idempotency keys. |
| **Merkle Hash Chained Audit Log** | PostgreSQL trigger-enforced append-only audit records, each linked via cryptographic hash chaining (`_prev_hash`, `_chain_hash`) with a 1-click `/v1/audit/verify` integrity checker. |
| **One-Click Windows Testbed** | Standalone launcher (`run_asg_testbed.bat` / `run_asg_testbed.ps1`) spins up Sandbox, Gateway, and Dashboard with zero Docker overhead. |

---

## ⚡ Quick Start

### Option A: One-Click Local Testbed (Recommended)
You can launch the entire stack (Gateway, Sandbox, and ASG-XDR Dashboard) immediately without Docker:

- **Double-click:** Run [`run_asg_testbed.bat`](run_asg_testbed.bat)
- **Or PowerShell:**
  ```powershell
  .\run_asg_testbed.ps1
  ```
- **What happens:**
  1. Tool Sandbox starts on `http://127.0.0.1:8001`
  2. ASG Security Gateway starts on `http://127.0.0.1:8000`
  3. **ASG-XDR SOC Dashboard & Attack Generator** starts on `http://127.0.0.1:8501`
  4. Your default browser opens automatically to the dashboard!

---

### Option B: Docker Compose Full Stack
For containerized multi-network isolation:
```powershell
# 1. Initialize local credentials
python -m scripts.init_demo

# 2. Run unit & regression test suite (74 tests)
python -m unittest discover -v

# 3. Start Linux-container Compose stack
docker compose up -d --build
```

---

## 🕹️ Interactive Threat Simulator & Dashboard

Click the **`[⚡ 프롬프트 발생기 제어]` (Traffic Generator)** button on the top-right of the ASG-XDR Dashboard to simulate live attacks:

1. **Assigned Document Read (`ALLOW` 200 OK):** Alice reads `report-alice-001`.
2. **Cross-Tenant Violation (`DENY` 403 Forbidden):** Alice attempts to read Bob's South-tenant document `report-bob-001` (`RESOURCE_OUT_OF_SCOPE`).
3. **Indirect Prompt Injection (`SUSPICIOUS` Content Masked):** Injected document `report-alice-attack` is inspected, flagged, and masked as `[WITHHELD]`.
4. **Unicode Zero-Width Obfuscation (`SUSPICIOUS`):** Normalizes `ig\u200Bnore...` evasion attempts before regex/n-gram scanning.
5. **Unapproved High-Risk Action (`REQUIRE_APPROVAL` 202 Accepted):** Blocks report transmission until an authorized reviewer clicks **[Approve]**.
6. **Merkle Hash Chain Verification (`VALID`):** Scans the audit chain and verifies zero tampering.

---

## 📚 Documentation & Specifications

- 📖 **[사용자 및 운영 설명서 (APP_MANUAL.md)](APP_MANUAL.md)**: 전체 시스템 개념, 네트워크 토폴로지, 6대 검증 시나리오, API 명세서 수록.
- 📐 **[v2.0 상세 설계 계획서 (DESIGN_SPECIFICATION_PLAN.md)](DESIGN_SPECIFICATION_PLAN.md)**: 제로 트러스트 위협 모델(T-01~T-07), 아키텍처 다이어그램, ERD 및 구현 로드맵.
- 🏛️ **[시스템 아키텍처 (docs/architecture.md)](docs/architecture.md)**
- 🎯 **[위협 모델 및 보안 경계 (docs/threat-model.md)](docs/threat-model.md)**
- 🔌 **[REST API 규격서 (docs/api.md)](docs/api.md)**

---

## 🔒 Security Notice

All documents, users (`alice`, `bob`), and sample outbox records in this repository are fictional. Never transmit real operational credentials, production tokens, or sensitive internal data to non-airgapped environments.

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
