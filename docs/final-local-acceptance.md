# Local acceptance assessment

**Assessment date:** 2026-10-01

**Result:** Local v1.0 acceptance is **not passed**.
**Scope:** Evidence gathered in the local Windows/Docker Desktop exercise. This is not a production certification. The user's explicit hold on GitHub publication remains in force.

## Decision

The core Gateway boundary, approval integrity, idempotency, audit controls, container isolation checks, recovery cases, dashboard JSON download, bounded resource soak, and preregistered L01-L04 matrix now have local evidence. The deterministic regex scanner misses the target. The optional local semantic prefilter measured 82% recall and 4% FPR on one author-created synthetic held-out set and is integrated into the host-run Agent adapter as a fail-closed auxiliary check; it never grants permissions. The four-arm study used only in-memory tools; baseline attacks all succeeded in that relaxed mock, while policy-only and full had no simulated attack success. Local commit/CI parity, complete 68-case suite mapping, README-only six-demo reproduction, clean-machine image-pull reproduction, and Git-history scan remain incomplete. Execution policy remains the security boundary.

## Acceptance evidence

| Criterion | Evidence | Result |
|---|---|---|
| Deterministic security cases | 34 local tests plus isolated Compose N01-N06, F01-F06, and B01-B04 evidence documented in [evaluation report](evaluation-report.md) | Passed for the enumerated cases; full planned 68-case matrix mapping remains incomplete |
| Unauthorized and duplicate side effects | Tested cross-tenant denial, two-process approval/idempotency races, and F01-F03 outage/recovery; observed no additional receipt/outbox entry in those scenarios | Passed for tested cases |
| Deterministic regex held-out input detection | `evaluation/results/rules-v4-heldout/metrics.json`; 50 malicious and 50 normal synthetic samples; recall 10%, FPR 8% | **Failed target:** below 80% recall and over 5% FPR |
| Optional semantic prefilter | `evaluation/results/llm-classifier-v4-heldout/metrics.json`; TP 41, FP 2, FN 9, TN 48; dataset has 20 label-pure families | Meets numeric target on this single synthetic set: recall 82%, FPR 4%; this is not an independent benchmark or authorization test |
| Historical held-out v1 | `evaluation/results/heldout-v1/metrics.json`; pre-tuning baseline | 8% recall; 0% FPR. This v1 set was subsequently used while tuning and is no longer independent evidence. |
| Tuned v1 diagnostic | `evaluation/results/diagnostic-v1-retuned/metrics.json` | 100% recall on the examples used during tuning; contaminated diagnostic only, excluded from acceptance claims |
| Actual local model integration | Host-run `qwen2.5-coder:7b` adapter with semantic filter enabled read a fictional report and saved a summary artifact; an attempted `send_report` was denied by Gateway with `DESTINATION_NOT_REGISTERED`. Classifier returned benign in 1.936s without an error. | One integrated run passed the normal read/save path and denied the unapproved submission. |
| L01-L04 four-arm matrix | 360/360 trials, 0 model errors. Baseline attack success 60/60 (100%) with 347 virtual submissions; prompt-only malicious success 0/60 but 108 submissions on normal cases; policy-only/full attack success 0/60 and 0 submissions. Each arm completed 30/30 normal summaries. | Preregistered 10-normal/20-malicious workload repeated three times per arm; side effects limited to in-memory mock records. Mock policy is not the Gateway service. |
| Gateway latency and concurrent security paths | B01-B04 results plus 180-second boundary soak are documented in [performance results](../evaluation/performance-baseline-2026-10-01.md), `evaluation/results/controlled-performance-2026-10-01.json`, and `evaluation/results/boundary-soak-2026-10-01-repeat.json` | 576/576 oversized requests received expected 413/422 responses; sampled Gateway memory ended 0.18 MB above the first sample, with a 3.08 MB transient sampled peak. Long-duration stability and production capacity remain unverified |
| Fresh-volume reproduction and repeat initialization | A separate Compose project initialized empty PostgreSQL/tool volumes and completed a fictional read. Automated R02 test reruns the initializer and confirms `.env` and database secret bytes remain unchanged. | Passed locally; clean-machine image-pull reproduction is not established |
| Source and application-image secret scan | Offline source scan plus `/app` payload scans of the built Gateway, migration, tool-sandbox, dashboard, and demo-agent images | No matches for the four configured high-confidence patterns. This did not scan base-image filesystems or Git history. |
| Git history / publication | Repository has no local commits and no remote configured; `.env` and generated database secrets are ignored | Git-history scan and R05 local commit/CI parity remain open. Stage 18 is explicitly held by the user. |

## Remaining acceptance gates

1. Preserve the classifier v4 result as a single synthetic evaluation only; run a new frozen set before any classifier tuning or broader performance claim.
2. Reconcile the six final-demo cases with the README and rerun them from a clean local state. L01-L04 is complete at 360 trials; its policy arm was virtual and is not an actual Gateway decision.
3. Keep longer-duration resource and production-capacity qualification open. The configured input boundaries passed a 180-second local soak.
4. Finish remaining R03-R05 evidence: Git-history review, local commit/CI parity, README-only six-demo reproduction, and clean-machine/image-pull proof. Dashboard export interaction is verified locally.
5. Re-run the acceptance table after the gates above pass. The source plan requires P0 security criteria and the initial performance/evaluation thresholds; this report does not waive them.
6. Stage 18 requires GitHub publication and a matching release tag. It remains on hold per the user's instruction and requires a later explicit go-ahead.

## Honest status

This repository is an implemented local reference MVP with substantial passing evidence, but it is **not project-complete under the plan's acceptance definition**. Do not label this state v1.0 or publish a release. The artifacts preserve both the passing local evidence and the measured gaps so work can resume without treating synthetic scanner scores as proof of safe execution.
