# Zero Trust AI Agent Security Gateway

A small, fictional security exercise that checks agent identity, task assignment, tool arguments, resource ownership, and human approval before a tool creates a local simulated side effect.

**Current implementation status:** local reference MVP pushed with its 61-commit history to the private GitHub repository [User-shin0328/AI-AGENT-SECURE](https://github.com/User-shin0328/AI-AGENT-SECURE), current commit `b67a1ff`. GitHub Actions run [#1](https://github.com/User-shin0328/AI-AGENT-SECURE/actions/runs/37471039211) passed both Python and Compose jobs and produced two retained artifacts. The repository is still private, so public URL availability and R04 public reproduction remain open. The optional host-side semantic prefilter now uses a validation-frozen local n-gram detector as an OR layer by default when enabled. On the pinned Agentic 5K dataset it measured 96.75% recall / 9.43% FPR on validation and 99.64% / 9.06% on held-out test, with zero test inference errors. The Qwen-only test result was 72.1% / 3.02%. On retained local semantic decisions, the combined detector preserved Qwen's v5/v6/v7 results (90%/2%, 88%/0%, 86%/0%); the n-gram model alone has weak recall on those local fixtures. A real adapter smoke run showed the n-gram layer catch an adversarial report that Qwen labeled benign; Gateway authorization still denied the unregistered destination. This classifier is auxiliary and never grants tool permissions. See the [local acceptance assessment](docs/final-local-acceptance.md) and [implementation report](docs/evaluation-report.md).

## Included

- A Python Gateway with opaque token authentication, server-owned principals, PostgreSQL runtime storage, and versioned migrations.
- Three fixed tools: `read_document`, `save_summary`, and reviewer-gated `send_report`.
- A separate service-authenticated tool sandbox with fictional documents, immutable artifacts, a simulated outbox, and execution receipts.
- Approval snapshots bound to artifact hash and policy version, with expiry and single-use consumption.
- Request idempotency and duplicate receipt handling.
- A deterministic prompt-injection pattern scanner whose verdict does not grant permissions.
- PostgreSQL runs on an internal Docker network with a restricted application role and append-only audit table. The tool sandbox keeps its local SQLite store.
- An optional bounded Ollama-compatible adapter and host-side fail-closed semantic input prefilter. The host adapter has completed a local fictional read/summary while the Gateway denied its unapproved report submission. In the preregistered 360-trial synthetic model study, baseline attacks succeeded in 60/60 relaxed mock trials; policy-only and full arms had 0/60 simulated attack successes. All relaxed tool effects were in-memory only; see the [matrix results](evaluation/results/agent-matrix-2026-10-01/supplemental-metrics.json).
- Loopback-only dashboard in Docker Compose. The Gateway API and tool sandbox are not published to the Windows host.
- Persistent token revocation with an administrator-only local rotation command; declarative policy is loaded and validated from `config/policy.yaml`.
- Reviewer dashboard can download the latest tenant-scoped audit events as JSON after an authenticated fetch.

## Quick start

See [the runbook](docs/runbook.md) for copyable Windows PowerShell commands that resolve Docker Desktop and Compose. Initialize ignored local credentials and database secrets with the containerized helper, then start the Linux-container Compose stack.

Run the code-level suite with `python -m unittest discover -v`. Check the working tree with `python -m scripts.check_secrets` and scan all reachable Git history with `python -m evaluation.scan_git_history`; the history scanner records matching object IDs and pattern classes without printing secret text.

The six final demo scenarios and their expected outcomes are listed in the [demo matrix](docs/final-demo-matrix.md). They use fictional documents and the local simulated outbox only.

## Architecture and limits

Read [architecture](docs/architecture.md), [threat model](docs/threat-model.md), [API contract](docs/api.md), [requirements traceability](docs/requirements.md), and the [preregistered model study](evaluation/agent-matrix-preregistration-2026-10-01.md). Gateway state uses PostgreSQL at runtime; SQLite is retained as the fast unit-test adapter, while the tool sandbox uses SQLite for simulated receipts and outbox. Local Docker verified read and reviewer-approved submit paths. A separate host-run model adapter was measured against a virtual in-memory tool harness; those mock-policy results do not replace the live Gateway's enforcement. The dashboard alone joins a host-facing network so its UI can bind to loopback; startup installs a default-drop output filter and runs the app without capabilities. A local probe verified loopback UI and internal Gateway access while blocking a public IPv4 TCP connection; see the [egress evidence](evaluation/results/dashboard-egress-2026-10-02.json) for scope and limits. No real email, firewall action tool, shell, arbitrary HTTP, or SQL tool is included. Local acceptance gaps and limits are listed in the [assessment](docs/final-local-acceptance.md).

Every report and user is fictional. Do not add real user documents, credentials, or operational logs to this exercise.

## License

MIT; see [LICENSE](LICENSE).

The dataset-derived evaluation model has separate CC BY 4.0 attribution terms; see [`demo_agent/models/NOTICE.md`](demo_agent/models/NOTICE.md).
