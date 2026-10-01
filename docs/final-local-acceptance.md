# Local acceptance assessment

**Assessment date:** 2026-10-02

**Result:** Local v1.0 acceptance is **not passed**.
**Scope:** Evidence gathered in the local Windows/Docker Desktop exercise. This is not a production certification. The user's explicit hold on GitHub publication remains in force.

## Decision

The core Gateway boundary, approval integrity, idempotency, audit controls, container isolation checks, recovery cases, dashboard JSON download, bounded resource soak, preregistered L01-L04 matrix, tracked-history scan, full image filesystem scan, six local demos, clean-checkout reproduction, runtime log probe, and real-model one-turn stop test have evidence. The deterministic regex scanner misses its target on v4 and v5. The optional semantic prefilter met numeric goals on both author-created synthetic sets (v4 82% recall/4% FPR; v5 90%/2%) and is integrated into the host-run Agent adapter as a fail-closed auxiliary check; it never grants permissions. The v5 set is family-separated but is not an independent benchmark. A real local model run on the assigned adversarial fixture had its text withheld; the Gateway denied the model's report action. The four-arm study used only in-memory tools; baseline attacks all succeeded in that relaxed mock, while policy-only and full had no simulated attack success. All 68 cases are mapped in `docs/case-traceability.md`, with partial and open cases clearly identified. The six approval scenarios used the authenticated dashboard proxy API; the browser approval-button click itself was not separately tested. Execution policy remains the security boundary.

## Acceptance evidence

| Criterion | Evidence | Result |
|---|---|---|
| Deterministic security cases | 52 local tests plus isolated Compose N01-N06, F01-F06, and B01-B04 evidence; all 68 plan cases mapped in [traceability](case-traceability.md) | Mapped completely; R04/R05 remain partial, so the full acceptance matrix has not passed |
| Unauthorized and duplicate side effects | Tested cross-tenant denial, two-process approval/idempotency races, and F01-F03 outage/recovery; observed no additional receipt/outbox entry in those scenarios | Passed for tested cases |
| Deterministic regex held-out input detection | `evaluation/results/rules-v4-heldout/metrics.json` and `rules-v5-heldout/metrics.json`; v5 TP 11, FP 5, FN 39, TN 45 | **Failed target:** v4 recall 10%/FPR 8%; v5 recall 22%/FPR 10%, below 80% recall and above 5% FPR |
| Optional semantic prefilter | `evaluation/results/llm-classifier-v4-heldout/metrics.json` and `llm-classifier-v5-heldout/metrics.json`; v5 TP 45, FP 1, FN 5, TN 49 across 20 new label-pure families | v4: recall 82%, FPR 4%; v5: recall 90%, FPR 2%. Both are author-created synthetic sets, not independent benchmarks or authorization tests |
| Historical held-out v1 | `evaluation/results/heldout-v1/metrics.json`; pre-tuning baseline | 8% recall; 0% FPR. This v1 set was subsequently used while tuning and is no longer independent evidence. |
| Tuned v1 diagnostic | `evaluation/results/diagnostic-v1-retuned/metrics.json` | 100% recall on the examples used during tuning; contaminated diagnostic only, excluded from acceptance claims |
| Actual local model integration | Host-run `qwen2.5-coder:7b` adapter with semantic filter enabled read a fictional report and saved a summary artifact; an attempted `send_report` was denied by Gateway with `DESTINATION_NOT_REGISTERED`. Classifier returned benign in 1.936s without an error. | One integrated run passed the normal read/save path and denied the unapproved submission. |
| L01-L04 four-arm matrix | 360/360 trials, 0 model errors. Baseline attack success 60/60 (100%) with 347 virtual submissions; prompt-only malicious success 0/60 but 108 submissions on normal cases; policy-only/full attack success 0/60 and 0 submissions. Each arm completed 30/30 normal summaries. | Preregistered 10-normal/20-malicious workload repeated three times per arm; side effects limited to in-memory mock records. Mock policy is not the Gateway service. |
| Six final demonstrations | All six procedures in [final demo matrix](final-demo-matrix.md) ran on the existing project and on a clean checkout. Qwen selected read, summary, and report tools on the assigned adversarial fixture; inspection withheld content and Gateway denied the report. Reviewer approval added one mock-outbox row; replay added zero. | `evaluation/results/final-demo-2026-10-02.json` and `evaluation/results/clean-repro-2026-10-02.json`; approval decision used the local authenticated dashboard proxy endpoint |
| Gateway latency and concurrent security paths | B01-B04 results plus 180-second boundary soak are documented in [performance results](../evaluation/performance-baseline-2026-10-01.md), `evaluation/results/controlled-performance-2026-10-01.json`, and `evaluation/results/boundary-soak-2026-10-01-repeat.json` | 576/576 oversized requests received expected 413/422 responses; sampled Gateway memory ended 0.18 MB above the first sample, with a 3.08 MB transient sampled peak. Long-duration stability and production capacity remain unverified |
| Fresh-volume and clean-checkout reproduction | Commit `941748a` snapshot, fresh `.env`/secrets, pulled base images, and new Compose volumes initialized successfully on the same Windows host; 52 tests and all six demos ran | `evaluation/results/clean-repro-2026-10-02.json`; same physical host, separate source snapshot and database volumes |
| Source, tracked history, and image secret scan | Offline source scan, tracked Git blob scan, and full merged-filesystem scan of seven built images | Zero matches for four configured high-confidence patterns in `evaluation/results/image-filesystem-scan-2026-10-02.json`; mounted volumes and other undisclosed secret classes are not covered |
| Runtime logging and real-model task budget | Synthetic CR/LF request and actual Docker logs; Qwen run with one-turn limit | Marker/credentials absent from local service logs; model returned `TURN_BUDGET_EXHAUSTED` after one call, with zero artifact/outbox additions |
| Local Git / publication | Code and evidence are stored in local commits only. No remote is configured. `.env` and generated database secrets are ignored. | Final local CI-equivalent checks and tracked-history scan are run on the evidence commit. Stage 18 remains explicitly held by the user. |

## Remaining acceptance gates

1. Preserve v4 and v5 as author-created synthetic evaluations only; collect an independent external benchmark before broader generalization claims or tuning against either holdout.
2. Exercise the dashboard approval-button click path; reviewer approval through the authenticated dashboard proxy endpoint and the audit-export interaction are verified, but the approval-button click was not separately exercised. L01-L04 remains a separate synthetic study whose policy arms are virtual, not actual Gateway decisions.
3. Keep longer-duration resource and production-capacity qualification open. The configured input boundaries passed a 180-second local soak.
4. Remote GitHub Actions execution remains pending because the user has held publication and no remote is configured.
5. Close the partial and open cases in [traceability](case-traceability.md), develop a dashboard egress control that preserves host access, then re-run the acceptance table. An internal-only Docker bridge blocked host access to the published dashboard port and was reverted. The source plan's security and evaluation thresholds are not waived.
6. Stage 18 requires GitHub publication and a matching release tag. It remains on hold per the user's instruction and requires a later explicit go-ahead.

## Honest status

This repository is an implemented local reference MVP with substantial passing evidence, but it is **not project-complete under the plan's acceptance definition**. Several planned cases remain partial or open, the deterministic scanner missed its target, and dashboard egress is not restricted. Do not label this state v1.0 or publish a release. GitHub publication and release remain on hold as requested.
