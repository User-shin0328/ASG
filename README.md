# Zero Trust AI Agent Security Gateway

A small, fictional security exercise that checks agent identity, task assignment, tool arguments, resource ownership, and human approval before a tool creates a local simulated side effect.

**Current implementation status:** local reference MVP; full plan acceptance is not passed and this is not a v1.0 release. The deterministic regex scanner measured 10% recall / 8% false-positive rate on v4 and 22% / 10% on a new v5 set. The optional local semantic prefilter measured 82% / 4% on v4 and 90% / 2% on v5; both sets are author-created synthetic evaluations, not independent benchmarks. The prefilter is auxiliary and never grants tool permissions. GitHub publication is on hold. See the [local acceptance assessment](docs/final-local-acceptance.md) and [implementation report](docs/evaluation-report.md).

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

See [the runbook](docs/runbook.md). Initialize ignored local credentials and database secrets with the containerized helper, then start the Linux-container Compose stack with `docker compose up --build -d`.

Run the code-level suite with `python -m unittest discover -v`.

The six final demo scenarios and their expected outcomes are listed in the [demo matrix](docs/final-demo-matrix.md). They use fictional documents and the local simulated outbox only.

## Architecture and limits

Read [architecture](docs/architecture.md), [threat model](docs/threat-model.md), [API contract](docs/api.md), [requirements traceability](docs/requirements.md), and the [preregistered model study](evaluation/agent-matrix-preregistration-2026-10-01.md). Gateway state uses PostgreSQL at runtime; SQLite is retained as the fast unit-test adapter, while the tool sandbox uses SQLite for simulated receipts and outbox. Local Docker verified read and reviewer-approved submit paths. A separate host-run model adapter was measured against a virtual in-memory tool harness; those mock-policy results do not replace the live Gateway's enforcement. The dashboard alone joins a host-facing network so its UI can bind to loopback; that network gives the dashboard container outbound network capability, which is not yet restricted. No real email, firewall, shell, arbitrary HTTP, or SQL tool is included. Local acceptance gaps and limits are listed in the [assessment](docs/final-local-acceptance.md).

Every report and user is fictional. Do not add real user documents, credentials, or operational logs to this exercise.

## License

MIT; see [LICENSE](LICENSE).
