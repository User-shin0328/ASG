# Local runbook

## Requirements

- Docker Desktop using Linux containers and Docker Compose.
- Python 3.12 or newer only if running the helper and tests directly on the host; initialization also runs in a container.

## Initialize and start

From the project root in PowerShell. The initialization step creates opaque demo tokens in `.env` and strong database secrets under the ignored `secrets/` directory; it keeps existing valid values and does not print secret values.

```powershell
docker run --rm --mount "type=bind,source=$($PWD.Path),target=/workspace" --workdir /workspace python:3.12-slim python -m scripts.init_demo
docker compose up --build -d
docker compose exec -T gateway python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3); print(r.status, r.read().decode())"
```

The first command uses the Python image already required by the project, so no host Python installation is needed to create local credentials.

Open the dashboard at `http://127.0.0.1:18501`. Read the reviewer token from the local ignored `.env` and enter it in the page. Load the audit events before downloading the JSON export; editing the reviewer token clears the previously fetched export data. Tokens are never committed. Only the dashboard is published to the Windows host, bound to loopback. The Gateway API and tool sandbox stay on internal Docker networks.

PostgreSQL starts on an internal data network with no host-published port. Compose runs the versioned migration job before starting the Gateway. The Gateway uses a restricted database role; the administrator password is used only during initial setup and migrations.

## Rotate a demo agent or reviewer token

Rotation revokes the existing token hash in PostgreSQL, replaces the selected value in the ignored local `.env`, and never prints the new token. Run this only after the stack is initialized. It briefly stops Gateway access while the token is replaced:

```powershell
docker compose stop gateway
docker compose --profile admin run --rm token-admin python /app/scripts/rotate_demo_token.py alice
docker compose up -d gateway
```

Use `bob` or `reviewer` instead of `alice` to rotate those credentials. The database keeps revoked hashes so restarting with an old token cannot reactivate it. The new credential is read from `.env` only by local services after the Gateway restarts.

The short-lived `token-admin` profile writes the mounted local `.env`; it uses a read-only container with only the `DAC_OVERRIDE` capability to support host file permissions. It joins only the internal data network and does not publish ports. Keep normal Gateway and agent containers unprivileged.

`config/policy.yaml` is YAML 1.2 written in JSON-compatible syntax so the runtime can parse it with Python's standard library. Startup rejects missing fields, unknown fields, invalid limits, a non-DENY default, or a report-submission rule without reviewer approval. Policy version, tool roles, argument fields, destinations, request/argument limits, the 60-second per-agent action budget, the pending-approval budget, and approval duration are loaded from this file. Budget exhaustion returns HTTP 429 before an action or tool side effect is recorded. Idempotent retries of an existing action return the existing action and do not consume another budget slot.

Gateway tool-service calls time out after 3 seconds by default. `TOOL_REQUEST_TIMEOUT_SECONDS` can override this from greater than 0 through 60 seconds; invalid values stop Gateway startup before it opens the database. The fault-injection Compose overlay uses 45 seconds only to provide a controlled restart window in the isolated test stack.

Docker Desktop needs a host-facing bridge for dashboard port forwarding, so the dashboard also joins `dashboard_host_net`. At startup, `dashboard/start.sh` resolves the fixed Gateway address, installs an nftables output chain with default-drop policy, then removes all capabilities and runs the app as UID 10003. The filter permits loopback, established replies to host-initiated connections, Docker's local DNS resolver, and the resolved Gateway IPv4 address on TCP 8000. If firewall setup or Gateway name resolution fails, the dashboard exits before serving the UI. The healthcheck requires both a default-drop chain and a successful local Gateway readiness request.

## Deterministic demo

```powershell
docker compose --profile demo run --rm demo-agent python -m demo_agent.deterministic --mode normal
docker compose --profile demo run --rm demo-agent python -m demo_agent.deterministic --mode injection
```

The normal example reads only Alice's assigned fictional report. The injection example records a suspicious string, then attempts Bob's report and receives a policy denial. The Gateway API is not published to the Windows host; use the demo-agent container for agent requests and the dashboard for reviewer approval. No external report transmission occurs.

### Six final scenarios

Follow the [six-case demo matrix](final-demo-matrix.md). The remaining deterministic commands are:

```powershell
docker compose --profile demo run --rm demo-agent python -m demo_agent.deterministic --mode unapproved-report
docker compose --profile demo run --rm demo-agent python -m demo_agent.deterministic --mode approval
docker compose --profile demo run --rm demo-agent python -m demo_agent.deterministic --mode execute-approved --action-id <action-id>
```

For scenario 3, run the optional host-side model against Alice's assigned adversarial fixture with the local model installed: `python -m demo_agent.llm_agent --document-id report-alice-attack --model qwen2.5-coder:7b`. It may not produce a malicious tool call; report its actual tool choice and Gateway result. The Gateway inspection and permission checks remain the enforcement evidence. Scenario 6 repeats the same `execute-approved` command and checks that the existing receipt is returned.

Run the isolated-agent and tool-authentication smoke checks with:

```powershell
docker compose --profile demo run --rm --no-deps demo-agent python -m demo_agent.network_checks
$toolNet = (docker network ls --filter "label=com.docker.compose.network=tool_net" --format "{{.Name}}" | Select-Object -First 1).Trim()
docker run --rm --network $toolNet ai-agent-security-gateway-demo-agent python -m demo_agent.network_checks --tool-auth
```

These checks require the profiled demo-agent image to be built. They confirm the agent can reach only the Gateway among the tested endpoints and that a client on the tool network without service credentials gets HTTP 401.

An optional model adapter is available with `python -m demo_agent.llm_agent --model qwen2.5-coder:7b`. Run it on the Windows host with Python 3.12 so the local model and dashboard loopback proxy are reachable. It expects Ollama at `OLLAMA_URL` (default `http://127.0.0.1:11434`) and forwards Gateway requests through `http://127.0.0.1:18501`. In PowerShell, load the local agent token without printing it with `$env:AGENT_ALICE_TOKEN = ((Get-Content .env | Where-Object { $_ -like 'AGENT_ALICE_TOKEN=*' }) -replace '^AGENT_ALICE_TOKEN=', '')`. The model service receives task text and tool results but no Gateway credential. The hardened Compose agent network deliberately cannot reach host services, including Ollama; enabling the semantic classifier inside that container therefore fails closed. On the host adapter only, set `$env:INPUT_CLASSIFIER_ENABLED = 'true'` to run the optional local prefilter before the task model and on retrieved document text. A classifier timeout, malformed response, or malicious verdict stops the task or withholds the document; this prefilter never grants tool permission. Its default timeout is 60 seconds to tolerate local model cold starts. Warm classification added about one second per checked input in the measured synthetic run; full-task latency depends on the model. Four exploratory actual-model runs are recorded in the implementation report; the deterministic adapter remains the repeatable baseline.

## Tests and shutdown

```powershell
python -m unittest discover -v
python -m evaluation.run
docker compose down
```

`docker compose down -v` also deletes demo state. Use it only when intentionally resetting the exercise. Never place production documents or credentials in these fixtures.
