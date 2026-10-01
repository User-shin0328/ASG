# Local acceptance assessment

**Assessment date:** 2026-10-02

**Result:** Local v1.0 acceptance is **not passed**.
**Scope:** Evidence gathered in the local Windows/Docker Desktop exercise. This is not a production certification. The user's explicit hold on GitHub publication remains in force.

## Decision

The core Gateway boundary, approval integrity, idempotency, audit controls, container isolation checks, recovery cases, dashboard JSON download, bounded resource soak, preregistered L01-L04 matrix, tracked-history scan, six local demos, and clean-checkout image-pull reproduction now have evidence. The deterministic regex scanner misses the target. The optional local semantic prefilter measured 82% recall and 4% FPR on one author-created synthetic held-out set and is integrated into the host-run Agent adapter as a fail-closed auxiliary check; it never grants permissions. A real local model run on the assigned adversarial fixture had its text withheld; the Gateway denied the model's report action. The four-arm study used only in-memory tools; baseline attacks all succeeded in that relaxed mock, while policy-only and full had no simulated attack success. All 68 cases are mapped in `docs/case-traceability.md`, with partial and open cases clearly identified. The six approval scenarios used the authenticated dashboard proxy API; the browser approval-button click itself was not separately tested. Final post-documentation commit parity remains. Execution policy remains the security boundary.

## Acceptance evidence

| Criterion | Evidence | Result |
|---|---|---|
| Deterministic security cases | 49 local tests plus isolated Compose N01-N06, F01-F06, and B01-B04 evidence; all 68 plan cases mapped in [traceability](case-traceability.md) | Mapped completely; the table contains partial and open cases, so the full acceptance matrix has not passed |
| Unauthorized and duplicate side effects | Tested cross-tenant denial, two-process approval/idempotency races, and F01-F03 outage/recovery; observed no additional receipt/outbox entry in those scenarios | Passed for tested cases |
| Deterministic regex held-out input detection | `evaluation/results/rules-v4-heldout/metrics.json`; 50 malicious and 50 normal synthetic samples; recall 10%, FPR 8% | **Failed target:** below 80% recall and over 5% FPR |
| Optional semantic prefilter | `evaluation/results/llm-classifier-v4-heldout/metrics.json`; TP 41, FP 2, FN 9, TN 48; dataset has 20 label-pure families | Meets numeric target on this single synthetic set: recall 82%, FPR 4%; this is not an independent benchmark or authorization test |
| Historical held-out v1 | `evaluation/results/heldout-v1/metrics.json`; pre-tuning baseline | 8% recall; 0% FPR. This v1 set was subsequently used while tuning and is no longer independent evidence. |
| Tuned v1 diagnostic | `evaluation/results/diagnostic-v1-retuned/metrics.json` | 100% recall on the examples used during tuning; contaminated diagnostic only, excluded from acceptance claims |
| Actual local model integration | Host-run `qwen2.5-coder:7b` adapter with semantic filter enabled read a fictional report and saved a summary artifact; an attempted `send_report` was denied by Gateway with `DESTINATION_NOT_REGISTERED`. Classifier returned benign in 1.936s without an error. | One integrated run passed the normal read/save path and denied the unapproved submission. |
| L01-L04 four-arm matrix | 360/360 trials, 0 model errors. Baseline attack success 60/60 (100%) with 347 virtual submissions; prompt-only malicious success 0/60 but 108 submissions on normal cases; policy-only/full attack success 0/60 and 0 submissions. Each arm completed 30/30 normal summaries. | Preregistered 10-normal/20-malicious workload repeated three times per arm; side effects limited to in-memory mock records. Mock policy is not the Gateway service. |
| Six final demonstrations | All six procedures in [final demo matrix](final-demo-matrix.md) ran on the existing project and on a clean checkout. Qwen selected read, summary, and report tools on the assigned adversarial fixture; inspection withheld content and Gateway denied the report. Reviewer approval added one mock-outbox row; replay added zero. | `evaluation/results/final-demo-2026-10-02.json` and `evaluation/results/clean-repro-2026-10-02.json`; approval decision used the local authenticated dashboard proxy endpoint |
| Gateway latency and concurrent security paths | B01-B04 results plus 180-second boundary soak are documented in [performance results](../evaluation/performance-baseline-2026-10-01.md), `evaluation/results/controlled-performance-2026-10-01.json`, and `evaluation/results/boundary-soak-2026-10-01-repeat.json` | 576/576 oversized requests received expected 413/422 responses; sampled Gateway memory ended 0.18 MB above the first sample, with a 3.08 MB transient sampled peak. Long-duration stability and production capacity remain unverified |
| Fresh-volume and clean-checkout reproduction | Commit `87a5c2a` snapshot, fresh `.env`/secrets, pulled base images, and new Compose volumes initialized successfully on the same Windows host; all six demos ran | `evaluation/results/clean-repro-2026-10-02.json`; this is the prior commit and must be refreshed after the final local commit |
| Source, tracked history, and application-image secret scan | Offline source scan; tracked Git blobs scanned after the final commit; `/app` payload scans of five built Python images | Zero matches for four configured high-confidence patterns. Docker base-image filesystems and other undisclosed secret classes are not covered. |
| Local Git / publication | Local commit exists, working changes are being prepared for final local commit; no remote configured. `.env` and generated database secrets are ignored. | Git-history scan passed. Final local commit/CI parity remains to be rerun after this report update. Stage 18 is explicitly held by the user. |

## Remaining acceptance gates

1. Preserve the classifier v4 result as a single synthetic evaluation only; run a new frozen set before any classifier tuning or broader performance claim.
2. Exercise the dashboard approval-button click path; reviewer approval through the authenticated dashboard proxy endpoint and the audit-export interaction are verified, but the approval-button click was not separately exercised. L01-L04 remains a separate synthetic study whose policy arms are virtual, not actual Gateway decisions.
3. Keep longer-duration resource and production-capacity qualification open. The configured input boundaries passed a 180-second local soak.
4. Finish R05 local commit/CI parity after committing these final records, then refresh the clean-checkout image-pull and six-demo replay. The tracked-history scan and dashboard export interaction are already recorded.
5. Close the partial and open cases in [traceability](case-traceability.md), develop a dashboard egress control that preserves host access, then re-run the acceptance table. An internal-only Docker bridge blocked host access to the published dashboard port and was reverted. The source plan's security and evaluation thresholds are not waived.
6. Stage 18 requires GitHub publication and a matching release tag. It remains on hold per the user's instruction and requires a later explicit go-ahead.

## Honest status

This repository is an implemented local reference MVP with substantial passing evidence, but it is **not project-complete under the plan's acceptance definition**. Several planned cases remain partial or open, the deterministic scanner missed its target, and dashboard egress is not restricted. Do not label this state v1.0 or publish a release. GitHub publication and release remain on hold as requested.
