# Threat model

## Assets and trust boundaries

- Protect fictional user reports, generated summaries, agent/reviewer credentials, task assignments, approval state, and action/receipt linkage.
- Treat the agent, document text, model output, request arguments, and tool response text as untrusted.
- Trust the host administrator, Gateway code/configuration, reviewer identity, and tool sandbox implementation for this exercise.
- Host root, Docker daemon compromise, kernel escape, and malicious Gateway operators are outside the current scope.

## Attacker capabilities

An attacker may add prompt injection to a document, alter tool names and arguments, claim another user or role in request JSON, replay or race requests, change data after approval, or attempt direct tool access.

## Controls implemented in the reference MVP

| Threat | Control | Evidence source |
|---|---|---|
| Spoofed identity or role | Opaque token maps to server-owned principal; strict action fields | `tests/test_gateway.py` |
| Cross-tenant document read | Task assignment and owner/tenant checks in Gateway and sandbox | same |
| Tool abuse | Fixed allowlist, strict per-tool arguments, fixed destination ID | same and sandbox receipts |
| Approval substitution/replay | Content hash, policy version, reviewer scope, expiration, single consumption | same |
| Request retry | Scoped idempotency key and tool execution receipt | same |
| Prompt injection | Versioned pattern scanner records verdict; policy remains independent | same |
| Untrusted rendered text | Dashboard HTML escaping and restrictive headers | `dashboard/index.html` |
| Unintended host exposure | Dashboard binds only to host loopback; Gateway, tool, and PostgreSQL APIs are not published | `compose.yaml`; local Docker inspection |

## Limits

The scanner is a small demonstration rule set with expected misses and false positives. It is not an LLM security classifier or DLP. PostgreSQL audit rows reject application-role update/delete/truncate, but a database or host administrator can still alter the database or its storage. The isolated local N01-N06 matrix covers documented service names, direct service addresses, selected host aliases/interface/port pairs, the default route, a public IPv4 TCP destination, tool authentication, capabilities, mounts, and the Docker socket. Those probes do not establish universal network isolation, IPv6/protocol coverage, or a host/Docker administrator boundary. Dashboard egress uses a default-drop nftables output chain with tested exceptions for loopback, established replies, Docker DNS, and the internal Gateway; its probe is limited to one public IPv4 TCP destination. Four exploratory actual-model runs and a separate 360-trial fictional workload study were performed; neither establishes broad model behavior or production risk rates. Local fault, approval, and cross-process stress results are documented in `docs/evaluation-report.md`; they are bounded single-host evidence, not production-capacity qualification.
