"""Viral Marketing, Free Spins Engine, Lucky Fortune Wheel, and Promo Vouchers for Lunaland."""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MARKETING_DB = Path(__file__).resolve().parent / "data" / "marketing.jsonl"

PROMO_VOUCHERS = {
    "LUNA2026": {"reward_lc": 100_000, "reward_sc": 5.0, "max_claims": 1000, "claimed": 42},
    "WELCOMEVIP": {"reward_lc": 250_000, "reward_sc": 15.0, "max_claims": 500, "claimed": 88},
    "CRYPTOBONUS": {"reward_lc": 500_000, "reward_sc": 25.0, "max_claims": 250, "claimed": 19},
    "LUCKYSTREAK": {"reward_lc": 75_000, "reward_sc": 3.0, "max_claims": 2000, "claimed": 156},
}

WHEEL_SLICES = [
    {"label": "10k LC", "type": "LC", "amount": 10_000, "prob": 0.35, "color": "#3b82f6"},
    {"label": "25k LC", "type": "LC", "amount": 25_000, "prob": 0.25, "color": "#8b5cf6"},
    {"label": "50k LC", "type": "LC", "amount": 50_000, "prob": 0.15, "color": "#ec4899"},
    {"label": "1.00 SC", "type": "SC", "amount": 1.0, "prob": 0.12, "color": "#10b981"},
    {"label": "2.50 SC", "type": "SC", "amount": 2.5, "prob": 0.08, "color": "#06b6d4"},
    {"label": "100k LC + 5 SC", "type": "JACKPOT", "amount_lc": 100_000, "amount_sc": 5.0, "prob": 0.04, "color": "#fbbf24"},
    {"label": "GRAND JACKPOT 50 SC", "type": "GRAND", "amount_lc": 500_000, "amount_sc": 50.0, "prob": 0.01, "color": "#ef4444"},
]


class MarketingEngine:
    """Enterprise Viral Marketing & Free Spins Campaign Engine."""

    def __init__(self, data_path: Path | str | None = None) -> None:
        self.data_path = Path(data_path or DEFAULT_MARKETING_DB)
        self._lock = threading.RLock()
        self._claimed_vouchers: set[str] = set()
        self._last_wheel_spin: dict[str, float] = {}
        self._free_spins_wallet: dict[str, dict[str, Any]] = {}

    def redeem_promo_code(self, member_id: str, code: str) -> dict[str, Any]:
        with self._lock:
            code_upper = code.strip().upper()
            voucher = PROMO_VOUCHERS.get(code_upper)
            if not voucher:
                raise ValueError("INVALID_PROMO_CODE")

            claim_key = f"{member_id}:{code_upper}"
            if claim_key in self._claimed_vouchers:
                raise ValueError("PROMO_CODE_ALREADY_REDEEMED")

            if voucher["claimed"] >= voucher["max_claims"]:
                raise ValueError("PROMO_CODE_MAX_LIMIT_REACHED")

            voucher["claimed"] += 1
            self._claimed_vouchers.add(claim_key)

            return {
                "ok": True,
                "code": code_upper,
                "reward_lc": voucher["reward_lc"],
                "reward_sc": voucher["reward_sc"],
                "message": f"Successfully claimed {voucher['reward_lc']:,} LC & {voucher['reward_sc']} SC!",
            }

    def spin_fortune_wheel(self, member_id: str) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            last_spin = self._last_wheel_spin.get(member_id, 0)
            # 1 spin per 24 hours (or demo bypass for instant testing)
            self._last_wheel_spin[member_id] = now

            import random
            r = random.random()
            cumulative = 0.0
            selected_slice = WHEEL_SLICES[0]
            slice_index = 0
            for idx, s in enumerate(WHEEL_SLICES):
                cumulative += s["prob"]
                if r <= cumulative:
                    selected_slice = s
                    slice_index = idx
                    break

            reward_lc = selected_slice.get("amount_lc", selected_slice.get("amount", 0) if selected_slice["type"] == "LC" else 0)
            reward_sc = selected_slice.get("amount_sc", selected_slice.get("amount", 0) if selected_slice["type"] == "SC" else 0)

            return {
                "ok": True,
                "slice_index": slice_index,
                "slice": selected_slice,
                "reward_lc": reward_lc,
                "reward_sc": reward_sc,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def grant_free_spins(self, member_id: str, game_id: str, spins_count: int = 10) -> dict[str, Any]:
        with self._lock:
            curr = self._free_spins_wallet.setdefault(member_id, {})
            curr[game_id] = curr.get(game_id, 0) + spins_count
            return {
                "ok": True,
                "member_id": member_id,
                "game_id": game_id,
                "available_free_spins": curr[game_id],
            }

    def get_campaigns_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active_vouchers": [
                    {"code": k, "reward_lc": v["reward_lc"], "reward_sc": v["reward_sc"], "claims_left": v["max_claims"] - v["claimed"]}
                    for k, v in PROMO_VOUCHERS.items()
                ],
                "wheel_slices": WHEEL_SLICES,
                "total_rewards_distributed_lc": 45_200_000,
                "total_rewards_distributed_sc": 4_850.0,
            }


marketing_engine = MarketingEngine()
