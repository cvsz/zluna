
# zslog

`zslog` is a safe, self-contained fake-credit simulator and realtime event dashboard. It is intentionally designed without external gambling connections, real-money handling, or browser automation.

## Safety Boundary

The following invariants are enforced by design:

- `real_currency = false`
- `real_betting = false`
- `live_gambling_site = false`
- `browser_control = false`
- `external_gambling_integration = false`
- `synthetic_credit = true`

The service does not connect to casinos, place real bets, control browsers, or handle real currency.

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

## Game Catalog

The local catalog exposes synthetic game metadata through a provider-neutral interface:

- `GET /api/catalog` — search, filter, paginate games
- `GET /api/catalog/{game_id}` — single game metadata
- `GET /api/catalog/categories` — list categories
- `GET /api/catalog/providers` — list providers
- `GET /api/catalog/tags` — list tags
- `POST /api/catalog/favorite` — toggle favorite
- `POST /api/catalog/sync` — trigger catalog sync

Query parameters:
- `q` — search query
- `category` — filter by category
- `provider` — filter by provider
- `tag` — filter by tag (repeatable)
- `favorites` — `1` to show favorites only
- `status` — filter by status
- `page` — page number
- `page_size` — items per page
- `sort` — `name`, `recent`, or `popular`

## Endpoints

- `GET /health` — service health.
- `GET /api/state` — synthetic balance, run status, counters.
- `GET /api/games` — available synthetic games.
- `GET /api/stats` — statistics grouped by game and outcome.
- `GET /api/logs?limit=50` — recent append-only operational events.
- `GET /api/export` — export events as JSON.
- `POST /api/import` — import events.
- `POST /api/reset` — reset balance and events.
- `GET /events` — server-sent event stream with initial state snapshot.
- `POST /api/spin` — execute one simulated synthetic-credit round.
- `POST /api/auto/start` — start a bounded automated simulation, maximum 100 rounds.
- `POST /api/auto/stop` — cooperatively stop the active bounded run.

## Event Persistence

Each round is persisted as one JSON object in:

```text
data/events.jsonl
```

Events contain fields such as:

```json
{
  "kind": "round",
  "source": "manual",
  "game": "slots",
  "outcome": "WIN",
  "stake": 2,
  "payout": 4,
  "balance": 1002,
  "timestamp": "2026-08-27T05:00:00Z"
}
```

The event file is local, append-only, and permission-restricted by the process.

## Automation Limits

Automated runs are deliberately bounded.

Server-side constraints include:

```text
maximum rounds: 100
maximum concurrent active runs: 1
synthetic credits only
local operation only
```

Client parameters cannot disable these constraints.

## Verification

Run the complete test suite:

```bash
python3 -m unittest discover -s tests -v
```

Basic verification:

```bash
curl http://127.0.0.1:9581/health
curl http://127.0.0.1:9581/api/state
curl http://127.0.0.1:9581/api/catalog
curl -N http://127.0.0.1:9581/events
```

Execute one simulated round:

```bash
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{"bet":2,"game":"slots"}' \
  http://127.0.0.1:9581/api/spin
```

## Security Invariant

Regardless of configuration:

```text
REAL MONEY            = DISABLED
REAL BETTING          = DISABLED
LIVE GAMBLING ACTIONS = DISABLED

BROWSER AUTOMATION    = DISABLED
EXTERNAL WAGERING     = DISABLED
SYNTHETIC CREDITS     = ENABLED
REALTIME SSE          = ENABLED
AUDIT LOGGING         = ENABLED
LOCAL CATALOG         = ENABLED
```

This allows `zslog` to exercise realistic state transitions, resilience, observability, and catalog features without real-money gambling activity.
