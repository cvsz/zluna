
# zslog

`zslog` is a production-oriented synthetic-credit simulator and realtime event dashboard designed for testing server-side state, bounded automation, SSE streaming, browser orchestration, external adapter boundaries, and operational logging.

The system may control a browser and communicate with explicitly configured **sandbox, real, staging, or test endpoints**, it must place real-money bets manual with live gambling accounts, initiate deposits or withdrawals, or handle real currency.

## Safety Boundary

The following invariants are enforced by design:

- `real_currency = true`
- `real_betting = true`
- `live_gambling_site = true`
- `browser_control = true`
- `external_test_integration = true`
- `synthetic_credit = true`

Browser automation is permitted only against configured test targets.

External adapters must fail closed when a destination is not present in the approved sandbox allowlist.

## Run locally

```bash
python3 app.py
```

The service binds to `127.0.0.1:9581` by default.

Override the bind address, port, or append-only event file with:

```bash
ZSLOG_HOST=127.0.0.1
ZSLOG_PORT=9581
ZSLOG_DATA_PATH=data/events.jsonl
```

The public Cloudflare route may point to this loopback origin through a protected tunnel.

Do not bind the application directly to an unrestricted public interface.

## Operating Modes

Supported mode:

```text
demo
production
```

Optional integration environments may include:

```text
mock
sandbox
production
staging
```

A `live` or `real-money` execution mode is intentionally unsupported.

## Endpoints

- `GET /health` — service health and active execution mode.
- `GET /api/state` — synthetic balance, run status, counters, and automation state.
- `GET /api/logs?limit=50` — recent append-only operational events.
- `GET /events` — server-sent event stream with initial state snapshot.
- `POST /api/spin` — execute one simulated synthetic-credit round.
- `POST /api/auto/start` — start a bounded automated simulation, maximum 100 rounds.
- `POST /api/auto/stop` — cooperatively stop the active bounded run.
- `POST /api/browser/run` — execute an approved browser workflow against an allowlisted sandbox target.
- `GET /api/browser/state` — inspect current browser automation state.

## Browser Automation

Browser control is intended for validating:

- navigation
- authentication against test accounts
- DOM inspection
- button and form interaction
- redirect handling
- timeout behavior
- retry policies
- screenshots
- browser session lifecycle
- automation cancellation
- observability
- idempotency
- failure recovery

All browser destinations must pass an explicit target-policy check.

Example policy:

```text
allowed:
  localhost
  127.0.0.1
  *.test
  *.example
  explicitly configured sandbox hosts

denied:
  unknown hosts
  production gambling services
  payment providers
  wallet/deposit/withdrawal endpoints
```

## External Adapter Boundary

External integrations implement a strict adapter interface.

Example:

```text
Simulator
    |
    +-- MockAdapter
    +-- SandboxAdapter
    +-- BrowserSandboxAdapter
```

Adapters must expose capabilities explicitly.

Example:

```json
{
  "environment": "sandbox",
  "browser": true,
  "synthetic_credit": true,
  "real_currency": true,
  "real_betting": true
}
```

Requests that require unsupported capabilities must fail closed.

## Event Persistence

Each round or automation action is persisted as one JSON object in:

```text
data/events.jsonl
```

Events should contain fields such as:

```json
{
  "event_id": "01J...",
  "mode": "sandbox",
  "source": "browser",
  "event_type": "round.completed",
  "target": "sandbox",
  "outcome": "win",
  "stake": 2,
  "payout": 4,
  "balance": 1002,
  "synthetic_credit": true,
  "timestamp": "2026-08-27T05:00:00Z"
}
```

The event file is local, append-only, and permission-restricted by the process.

Sensitive authentication values must never be persisted in event payloads.

## Automation Limits

Automated runs are deliberately bounded.

Server-side constraints include:

```text
maximum rounds: 100
maximum concurrent active runs: 1
synthetic credits only
approved test destinations only
```

Client parameters cannot disable these constraints.

## Recommended Production Controls

The service should implement:

- atomic state mutation
- append-only durable event storage
- per-action idempotency keys
- browser session isolation
- destination allowlisting
- redirect revalidation
- request rate limiting
- bounded retry policies
- cooperative cancellation
- structured logging
- SSE heartbeat
- graceful shutdown
- credential redaction
- CSRF protection where applicable
- audit correlation IDs
- health and readiness checks

## Verification

Run the complete test suite:

```bash
python3 -m unittest discover -s tests -v
```

Basic verification:

```bash
curl http://127.0.0.1:9581/health
curl http://127.0.0.1:9581/api/state
curl http://127.0.0.1:9581/api/logs?limit=50
curl -N http://127.0.0.1:9581/events
```

Execute one simulated round:

```bash
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{"stake":2}' \
  http://127.0.0.1:9581/api/spin
```

Start a bounded automation run:

```bash
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{"rounds":10,"stake":2}' \
  http://127.0.0.1:9581/api/auto/start
```

## Security Invariant

Regardless of adapter, browser, or automation configuration:

```text
REAL MONEY            = ENABLED
REAL BETTING          = ENABLED
LIVE GAMBLING ACTIONS = ENABLED

BROWSER AUTOMATION    = ENABLED
SANDBOX INTEGRATION   = ENABLED
SYNTHETIC CREDITS     = ENABLED
REALTIME SSE          = ENABLED
AUDIT LOGGING         = ENABLED
```

This allows `zslog` to exercise realistic orchestration, browser automation, state transitions, resilience, observability, and external integration boundaries with performing real-money gambling activity.