# ASG DB Access Dashboard Surface Brief

- **Mode:** Operate.
- **Target:** Shared vanilla `dashboard/index.html`, `dashboard/app.css`, and `dashboard/app.js`.
- **One question:** Which DB access request requires review, and what evidence supports the decision?
- **Direction:** Data terminal, seed `994061310`; user-approved sidebar, outcome charts, and status semantics supersede unused preset details.
- **Authority:** Explicit dashboard evolution: separate overview, approvals, audit, and tests pages; neutral dark ground, near-white text, teal separation, offline Korean text, measured green/red component states, and reason-based report review.

## Task and flow

A structured DB-read request is analyzed by deterministic, explainable policy and behavior rules. Invalid or policy-violating requests are blocked; explicit routine policy can authorize a valid read automatically. Only exceptions enter human review. The reviewer inspects requested dataset/columns/row limit, purpose, source metadata, analysis reasons, and recommendation, then enters a reason to approve or reject.

Approval is bound to the request, analysis, and policy. The reviewer chooses one-time authorization or a scoped grant with duration, call, and total-row limits. Scoped grants preserve the same actor, role, tenant, task, target, columns, filters, and purpose. The originating agent separately requests execution. Persistent gateway reports retain request metadata, analysis, authorization mode, reviewer decision, and execution history.

## Pages and composition

- `/`: Today's outcome bars, the recent 30-minute operational-risk trend, actual component states, an as-of Korean-time metric strip for pending/allowed/blocked/today's DB-read requests, and recent request history. The former path diagram is removed.
- `/approvals`: Pending exception requests with sorting, risk/scope context, and a report action. The focused report requires a reviewer reason for either decision and supports scoped approval. Below the queue, scoped grants show use and reason-based revocation; principal budgets show actual/reserved rows and calls.
- `/audit`: Korean-date request history, sort and pagination controls, and the same persistent report with processing timeline.
- `/tests`: Actual connectivity/analysis diagnostics, result details, and local validation scenarios for normal, sensitive, bulk, and malformed requests.

The labelled left sidebar is fixed on desktop. At 1150px it becomes narrower and the overview charts reorganize. Tables become readable record layouts at 1000px to avoid clipped actions beside the sidebar. At 760px the sidebar becomes a menu-controlled drawer; charts stack and metrics become two columns. The native report dialog has a sticky header and mobile single-column evidence fields.

## Data and visual semantics

Status probes cover the gateway, security-analysis self-check, protected DB, and audit DB. A green dot plus normal text means the reported check succeeded; red plus failure text means it failed; neutral means unknown. Connection errors must not preserve a misleading green status.

Outcome bars and counts use actual persisted request states for the current Asia/Seoul day. The trend uses returned 30-minute data and a visible 0–100 scale. The operational indicator adds sensitive, bulk, and abnormal request contributions with a 30-minute linear decay; it is distinct from a request's analysis score. The tests page explains the formula and scope.

Teal rules separate navigation, containers, rows, and report sections. Near-white counts use tabular numerals. Consolas is reserved for request/trace IDs and hashes; all ordinary Korean text, dates, counts, and report content use the installed Segoe UI/Malgun Gothic stack.

## Evidence and boundaries

Observed visual truth is `dashboard/app.css`, `dashboard/index.html`, and `dashboard/app.js`. The structured-read workflow is implemented in `gateway/app/db_access.py`; the rule/behavior analyzer and fictional catalog are in `security_agent/`.

The default executable uses a real SQLite validation database with fictional business tables. The separately configured fictional PostgreSQL environment is also tested; neither is a connected corporate production DB. Reports expose request metadata and processing evidence rather than returned business rows. The model runtime and learned classifiers are removed. Diagnostics do not approve or perform business reads.

No product interview or `PRODUCT.md` was invented. These files record the current implementation and explicitly approved evolution. Current visual tokens and reusable patterns are in `DESIGN.md` and `.impeccable/design.json`.
