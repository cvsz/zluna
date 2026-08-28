# ADR 0001: Synthetic Dual-Currency Architecture and Provably Fair RNG

- Status: Accepted
- Date: 2026-08-28
- Owners: @cvsz

## Context

`zluna` operates as an enterprise-grade social casino simulator. It requires realistic wagering mechanics, user level progression, daily streak retention, and real-time multiplayer telemetry without handling real money, external gambling integration, or browser automation.

## Decision

1. **Dual-Currency Model**:
   - **Luna Coins (LC)**: Synthetic free-play currency granted daily and through gameplay for entertainment and leaderboard ranking.
   - **Sweeps Coins (SC)**: Promotional sweeps currency earned through gift bonuses or store packages, strictly simulated with a 1.00 SC = 1 USD synthetic prize redemption benchmark.
2. **Provably Fair RNG**:
   - Every round outcome is generated using HMAC-SHA256 based on a server seed, client seed, and nonce.
   - The result hash is committed before the round and revealed to the client for cryptographic verification.
3. **Local Append-Only Persistence**:
   - All state mutations are synchronized via Python `threading.RLock` and written directly to local append-only JSON Lines ledgers in `data/`.

## Alternatives considered

- **Single Currency Model**: Insufficient to model real-world US/Global social sweeps casino mechanics.
- **Relational SQL Database (SQLite/PostgreSQL)**: Unnecessary operational overhead for lightweight, zero-dependency, self-contained demonstration and deterministic audit logging.

## Consequences

- **Positive**: Zero risk of real-money gambling liabilities, 100% deterministic testability, low memory footprint, and instant replayability from log files.
- **Operational**: High-throughput SSE streaming directly off the in-memory state with minimal CPU load.
- **Security**: Invariants strictly enforce `real_money = False` and fail-closed validation on invalid bet inputs.

## Validation

- Automated pytest matrix (`tests/test_enterprise.py`) validates cryptographic seed integrity, streak multipliers, and ledger replayability across 28 test suites.
