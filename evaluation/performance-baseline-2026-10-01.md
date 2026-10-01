# Local performance measurements — 2026-10-01

This is a development-host observation, not a production capacity claim.

## Method

- Environment: Windows Docker Desktop, current local Compose stack; single sequential client inside the Gateway container.
- Workload: 300 fresh HTTP requests to `GET /health/live`, timed end-to-end from Python's standard-library client.
- Resource snapshot: one `docker stats --no-stream` sample immediately after the request loop.
- Exclusions: authentication/database lookups, action creation, tool execution, reviewer decisions, concurrency, sustained duration, and host CPU accounting.

## Observed result

| Measure | Observation |
|---|---:|
| Requests | 300 |
| Elapsed | 0.201 s |
| Throughput | 1,492.33 requests/s |
| Latency p50 | 0.610 ms |
| Latency p95 | 0.721 ms |
| Maximum observed latency | 14.855 ms |

Container resource snapshot:

| Service | CPU | Memory |
|---|---:|---:|
| Gateway | 0.01% | 31.19 MiB |
| PostgreSQL | 0.00% | 23.13 MiB |
| Tool sandbox | 0.01% | 14.88 MiB |
| Dashboard | 0.01% | 17.34 MiB |

These figures cover only process liveness on one warm local Docker run.

## Sustained authenticated input-inspection workload

The second workload ran inside the Gateway container against `POST /v1/inputs/inspect` with Alice's already configured demo credential. Each request inspected a harmless fictional-workflow sentence. It exercised authentication, inspection, and audit persistence; it did not call the tool sandbox or create a document artifact, approval, or outbox entry.

Method: 10-second paced warm-up at 20 requests/second, then 1,200 paced requests over 60 seconds at 20 requests/second, 10 client workers, three independent measured runs. Latency is measured client-side from request start through response body. Errors and completed work are counted. CPU is the Gateway container cgroup CPU-time delta during the measured interval; peak memory is the container cgroup high-water mark, which spans the current container lifetime and is not isolated to each run.

| Run | Completed / offered | Actual requests/s | Errors | p50 | p95 | Max | CPU seconds | Container peak memory |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1,200 / 1,200 | 20.015 | 0 | 3.699 ms | 4.561 ms | 77.108 ms | 3.985 | 71,634,944 bytes |
| 2 | 1,200 / 1,200 | 20.015 | 0 | 3.518 ms | 4.361 ms | 18.026 ms | 3.833 | 71,634,944 bytes |
| 3 | 1,200 / 1,200 | 20.015 | 0 | 3.555 ms | 4.471 ms | 43.438 ms | 3.594 | 71,634,944 bytes |

The observed p95 is below the plan's initial 150 ms Gateway pre-execution target for this route and this local stack. This inspection workload alone does not stand in for normal document reads or approval execution. The additional B02-B04 checks are recorded below. None of these results establish production capacity or long-duration stability. Reproduce the inspection run from the repository root by piping `evaluation/performance_load.py` to `python -` inside the running `gateway` container; the script sends no tool action.

## Denial burst, size boundaries, and approved execution concurrency

**B02 denial burst:** `evaluation/denial_load.py` sent 200 paced warm-up requests, then 1,200 cross-tenant document-read attempts at 20 requests/second for 60 seconds with 10 workers to the running local Gateway. All 1,200 measured requests returned the expected HTTP 403; actual rate was 20.015 requests/second, p50 4.057 ms, p95 4.819 ms, max 69.639 ms. The separate tool sandbox counts remained `artifacts/outbox/receipts = 7/2/18` before and after. The requests did create denial/action audit records in the local demo Gateway database; no tool call was dispatched.

**B03 size boundaries:** `evaluation/boundary_checks.py` received HTTP 413 `REQUEST_TOO_LARGE` for a request over the 24,000-byte limit and HTTP 422 `INVALID_ARGUMENTS` for summary content over the 8,000-character limit. Both were rejected before an action or tool side effect.

**B04 approved execution concurrency:** `evaluation/approval_concurrency.py` ran against the isolated `gateway-fault-test` PostgreSQL and tool volumes. A fictional summary was saved, a report was approved, and 20 concurrent execution requests (10 workers) targeted the same approved action. All returned HTTP 200 / `SUCCEEDED`, with one unique receipt ID. Tool counters moved from `0/0/5` to `1/1/7` for `artifacts/outbox/receipts`: one artifact, one approved mock-outbox entry, and two receipts (one for save and one for submit). There were no duplicate submission side effects. The test dashboard could not bind loopback port 18501 because the main dashboard already owns it; the isolated Gateway, PostgreSQL, and tool sandbox were healthy and sufficient for this API-only test.

These checks supply local evidence for B02, B03, and B04. The normal-read B01 measurement follows. The isolation and concurrency claims apply only to these local fictional records and measured requests.

## Boundary/resource soak

On 2026-10-01, the local dashboard proxy received 576 synthetic oversized requests over 180 seconds at a 250 ms request interval. Of 288 oversized bodies, all returned HTTP 413; of 288 over-limit summary arguments, all returned HTTP 422 `INVALID_ARGUMENTS`. No tool-side effects were requested or accepted. Gateway container memory was sampled every five seconds: first sample 32,988,200 bytes, final sample 33,176,944 bytes (+188,744 bytes), with a transient peak 3,082,814 bytes above the first sample. Full sample data and per-case latency are in [`results/boundary-soak-2026-10-01-repeat.json`](results/boundary-soak-2026-10-01-repeat.json). This is a short local soak of the configured boundaries, not a production capacity or long-duration stability claim.

**B01 assigned document-read load:** `evaluation/read_load.py` ran against the isolated test Compose stack. Three runs each used a 10-second paced warm-up followed by 1,200 reads over 60 seconds at 20 requests/second and 10 workers. All 3,600 actions returned HTTP 200 / `SUCCEEDED`; actual rate was 20.012 requests/second in each run. p50 was 13.161–13.277 ms and p95 was 16.104–16.533 ms. Per-run Gateway CPU time was 6.443–6.742 seconds; container lifetime peak memory across the runs was 61.0–62.0 MiB. Sandbox counters moved from `artifacts/outbox/receipts = 1/1/7` to `1/1/4207`: only the expected 3,600 read receipts increased; no artifact or outbox entry was added.

The measured B01 p95 was below the plan's initial 150 ms target on this fictional local workload. Results for all four B cases are serialized in [`results/controlled-performance-2026-10-01.json`](results/controlled-performance-2026-10-01.json). Extended memory/size soak, longer duration, and production capacity remain out of scope for these runs.
