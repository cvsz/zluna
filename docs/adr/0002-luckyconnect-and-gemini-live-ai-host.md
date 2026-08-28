# ADR 0002: LuckyConnect Aggregation Protocol & Gemini Live Voice AI Host

- Status: Accepted
- Date: 2026-08-28
- Owners: @cvsz

## Context

To provide a modern, production-grade social gaming experience, `zluna` requires multi-provider game aggregation simulation (LuckyStreak, Pragmatic Play, PG Soft, Yggdrasil, Red Rake, RubyPlay, Relax Gaming) and real-time interactive voice commentary for live dealer tables and high-volatility slots.

## Decision

1. **LuckyConnect Aggregation Engine**:
   - Implemented standard Hawk Authentication (`Hawk id="...", ts="...", nonce="...", mac="..."`) for secure round launching.
   - Built a dynamic universal game simulation router (`src/games.py`) handling all 6,000+ catalog titles dynamically across Live Dealer, Slots, Crash, Table, and Arcade categories.
   - Exposed seamless debit/credit webhook callbacks (`/api/luckyconnect/webhook`) for studio round settlement.
2. **Gemini Live Multimodal Voice AI Host**:
   - Integrated `Luna AI Live Host` (`src/ai_dealer.py`) with real-time contextual commentary, player sentiment reactions, and browser-native speech synthesis.
   - Provided instant advice and lucky number suggestions via `/api/ai-dealer/commentary`.

## Alternatives considered

- Static alerts or mock iframe popups without real game rules.
- Pre-recorded static MP3 audio loops instead of dynamic generative voice commentary.

## Consequences

- **Positive**: Immersive studio experience matching modern Las Vegas / Macau tier-1 live casinos with zero external third-party API dependencies or cost leaks.
- **Operational**: Fully self-contained local simulation compatible with Cloudflare Edge tunneling.

## Validation

- End-to-end integration tests in `tests/test_enterprise.py` verify Hawk session signing, webhook balance settlement, and AI Dealer voice generation.
