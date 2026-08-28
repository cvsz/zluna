# Architecture: zluna Enterprise Social Casino Engine

## 1. System Overview

`zluna` (Lunaland Next-Gen) is a self-contained, enterprise-grade social casino simulator and realtime event telemetry platform.

```
┌────────────────────────────────────────────────────────┐
│               Public Ingress: zluna.zeaz.dev           │
│                 (Cloudflare Edge Tunnel)               │
└───────────────────────────┬────────────────────────────┘
                            │ :9581
┌───────────────────────────▼────────────────────────────┐
│         zluna Realtime Server (ThreadingHTTPServer)     │
│         - SSE Broadcast Hub (/events)                  │
│         - REST Control APIs (/api/*)                   │
├───────────────────────────┬────────────────────────────┤
│   Provably Fair RNG       │    LuckyConnect 6k+        │
│   (HMAC-SHA256 Seed/Hash) │    (Hawk Auth Aggregator)  │
├───────────────────────────┼────────────────────────────┤
│   Dual-Currency Vault     │    Gemini Live AI Dealer   │
│   (LC / SC Ledger)        │    (Multimodal Voice Host) │
├───────────────────────────┼────────────────────────────┤
│   Marketing & Tournaments │    Risk & Fraud Radar      │
│   (Fortune Wheel, Drops)  │    (Studio P&L Telemetry)  │
└───────────────────────────┴────────────────────────────┘
```

## 2. Core Subsystems

1. **`src/app.py` & `src/main.py`**:
   - High-concurrency `ThreadingHTTPServer` with non-blocking SSE streaming and request parsing.
2. **`src/games.py` & `src/catalog.py`**:
   - Universal Dynamic Simulator supporting 36 certified games (Slots, Live Dealer Blackjack VIP, European Roulette, Baccarat, Plinko, Crash, Ancient Tumble Megaways, Sugar Rush 1000, Gates of Olympus 1000).
3. **`src/luckyconnect.py`**:
   - Enterprise Hawk-authenticated aggregator proxying 6,000+ titles with seamless debit/credit webhook round settlements.
4. **`src/zwallet.py`**:
   - Multi-chain cryptocurrency deposit simulation (ETH, TRX, SOL, POL) and Sweeps Coin APY staking vault.
5. **`src/members.py`**:
   - PBKDF2-HMAC-SHA256 authentication, session token issuance, KYC tiers, and TOTP 2FA.
6. **`src/ai_dealer.py`**:
   - Gemini Live Multimodal Voice AI Host providing real-time game commentary, player sentiment reactions, and audio speech synthesis.
7. **`src/marketing.py` & `src/tournaments.py`**:
   - Daily Cosmic Fortune Wheel, progressive streak rewards, promo voucher redemption, and dynamic tournament leaderboard drops.
8. **`src/risk_analytics.py`**:
   - Studio GGR/NGR P&L matrix, velocity fraud detection, and OCR KYC verification.

## 3. Data Integrity & Persistence

- **Append-Only Event Ledger**: All rounds and transactions are written atomically to `data/events.jsonl` and auxiliary JSONL ledgers with `RLock` synchronization.
- **Provably Fair**: Every spin generates verifiable client/server seed pairs and SHA-256 result hashes.

## 4. Operational Invariants

- **Real Money**: DISABLED (Synthetic LC and SC only).
- **External Gambling**: DISABLED.
- **Safety**: Fully safe, local, and sandbox-isolated.
