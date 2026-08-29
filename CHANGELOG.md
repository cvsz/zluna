# Changelog

All notable changes to `zluna` (Lunaland Next-Gen) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-08-29

### Added
- **Multi-Language Internationalization (i18n)**: Native 6-language dictionary and runtime switcher (EN, TH, JA, ZH, ES, PT) with `GET /api/i18n?lang={code}`.
- **Social Bot Integrations**: Telegram Mini-App URL launch token generator (`GET /api/bots/miniapp`) and Discord Big Win (>=10x) rich embed notification hub.
- **Deep Pentest & Security Hardening**: Constant-time timing-attack mitigation on credentials and Hawk HMACs, fail-closed bet boundary fuzzing protection, and zero-leak credential isolation.
- **Supply Chain Security**: OpenSSF Scorecard automated analysis and CycloneDX SBOM provenance tracking workflows.

## [2.0.0] - 2026-08-28

### Added
- **Gemini Live Multimodal Voice AI Host**: Realtime game commentary, dynamic sentiment reactions, audio cues, and voice host HUD banner.
- **Universal Dynamic Simulation Router**: 36 certified real-world titles across LuckyStreak Live Studios, Pragmatic Play 1000s, PG Soft, Yggdrasil, Red Rake, RubyPlay, and Relax Gaming.
- **LuckyConnect Aggregator**: Hawk-authenticated 6,000+ game catalog integration with seamless debit/credit webhook callbacks.
- **Keyless Gaming Hub**: Non-blocking asynchronous aggregated feeds from CheapShark, FreeToGame, GamerPower, and OpenCritic.
- **ZWallet Crypto Engine**: Multi-chain deposit simulations (ETH, TRX, SOL, POL) and Sweeps Coin APY staking vault.
- **Viral Marketing & Engagement**: Daily Cosmic Fortune Wheel (50 SC top prize), streak bonuses, and promo code redemption engine.
- **Risk Radar & Studio P&L**: Autonomous velocity fraud detection and realtime GGR/NGR analytics matrix.
- **Modular Directory Structure**: Refactored all Python source code into `src/*.py`.

### Changed
- Rebranded entire project, documentation, endpoints, and system units from `zslog` to `zluna`.
- Updated public ingress to `https://zluna.zeaz.dev`.

### Security
- GPG signed commits on all releases.
- CodeQL automated SAST security analysis passed 100%.
- Zero tracked secret credentials.
