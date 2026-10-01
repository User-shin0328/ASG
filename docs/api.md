# API reference (MVP)

Use `Authorization: Bearer <token>` for protected routes. Agent action requests also require `Idempotency-Key`. Agent, reviewer, and internal tool credentials are separate. `/health/ready` checks the local store and the tool service before returning ready.

| Method and path | Access | Purpose |
|---|---|---|
| `GET /health/live` | public | Process liveness |
| `GET /health/ready` | public | Current process readiness |
| `POST /v1/inputs/inspect` | agent | Record deterministic input inspection |
| `POST /v1/actions` | agent | Validate, decide, and execute or queue an action |
| `GET /v1/actions/{action_id}` | owning agent or reviewer | Read action state |
| `POST /v1/actions/{action_id}/execute` | owning agent | Execute a ready, approved action |
| `GET /v1/approvals` | reviewer | List pending approvals with exact summary body, destination, and hash |
| `POST /v1/approvals/{approval_id}/decision` | reviewer | Body: `{"decision":"approve"}` or reject |
| `GET /v1/audit/events` | reviewer | Read latest masked audit events |

Example action:

```json
{"task_id":"task-alice-001","tool":"read_document","arguments":{"document_id":"report-alice-001"}}
```

Outcomes distinguish policy decisions (`ALLOW`, `DENY`, `REQUIRE_APPROVAL`) from states (`READY`, `PENDING_APPROVAL`, `EXECUTING`, `SUCCEEDED`, `UNKNOWN`, and terminal rejection/failure states). HTTP 401 means unauthenticated, 403 means denied, 409 means idempotency/state conflict, 413 means oversized input, 422 means invalid schema, 429 means the per-agent action or pending-approval budget is exhausted, and 503 means a required tool service is unavailable. Existing idempotent retries return their original result without consuming an additional action-budget slot.

The internal `tool-sandbox` API is service-token protected and is not published to the host. It supports only fixed registered tools and simulated artifacts/outbox; it never accepts URLs, paths, SQL, or shell commands from the agent.
