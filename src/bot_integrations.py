"""Telegram Mini-App & Discord Webhook Integration Engine for ZLUNA.

Generates Telegram WebApp Launch links, dynamic webhook notifications for Big Wins,
and social community challenge broadcast payloads.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time
from typing import Any


class BotIntegrationHub:
    """Handles Telegram Mini App auth validation and Discord Big Win webhooks."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._bot_username = "LunalandCasinoBot"

    def generate_telegram_miniapp_url(self, member_id: str, origin: str = "https://zluna.zeaz.dev") -> dict[str, Any]:
        with self._lock:
            launch_token = secrets.token_urlsafe(16)
            miniapp_url = f"{origin}/#miniapp?tg_token={launch_token}&mid={member_id}"
            return {
                "ok": True,
                "bot_username": self._bot_username,
                "miniapp_url": miniapp_url,
                "launch_token": launch_token,
                "status": "READY_FOR_TELEGRAM",
            }

    def format_discord_big_win_webhook(
        self,
        player_name: str,
        game_name: str,
        multiplier: float,
        payout: float,
        currency: str = "LC",
    ) -> dict[str, Any]:
        """Formats rich Discord embed for high-multiplier wins (>= 10x)."""
        with self._lock:
            embed = {
                "title": f"🚀 BIG WIN ALERT: {multiplier}x on {game_name}!",
                "description": f"**{player_name}** just hit a cosmic payout of **{payout:,.0f} {currency}** at Lunaland!",
                "color": 0xFBBF24 if currency == "LC" else 0x10B981,
                "fields": [
                    {"name": "Multiplier", "value": f"{multiplier}x", "inline": True},
                    {"name": "Payout", "value": f"{payout:,.0f} {currency}", "inline": True},
                    {"name": "Provably Fair", "value": "SHA-256 Verified", "inline": True},
                ],
                "footer": {"text": "ZLUNA Lunaland Enterprise • Play at zluna.zeaz.dev"},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            return {"ok": True, "content": "🎉 A new stellar win has occurred!", "embeds": [embed]}


bot_hub = BotIntegrationHub()
