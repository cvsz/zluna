"""Telegram Mini-App & Discord Bot Integration Engine for ZLUNA.

Full mini-app interfaces for instant social gameplay via Telegram and Discord.
Includes command handlers, game launching, balance checks, and webhook notifications.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any


class TelegramMiniApp:
    """Telegram Mini-App interface for Lunaland."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._bot_username = "LunalandCasinoBot"
        self._sessions: dict[str, dict[str, Any]] = {}
        self._webhook_url = "https://zluna.zeaz.dev/api/bots/telegram/webhook"

    def validate_init_data(self, init_data: str, bot_token: str) -> dict[str, Any]:
        """Validate Telegram WebApp initData using HMAC-SHA256."""
        with self._lock:
            try:
                pairs = init_data.split("&")
                data_check_string = ""
                hash_value = ""
                for pair in pairs:
                    key, value = pair.split("=", 1)
                    if key == "hash":
                        hash_value = value
                    else:
                        data_check_string += f"\n{key}={value}"
                data_check_string = data_check_string.lstrip("\n")
                secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
                computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
                if computed_hash == hash_value:
                    return {"ok": True, "valid": True}
                return {"ok": True, "valid": False}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    def create_miniapp_session(self, member_id: str, tg_user_id: int, origin: str = "https://zluna.zeaz.dev") -> dict[str, Any]:
        with self._lock:
            session_token = secrets.token_urlsafe(32)
            self._sessions[session_token] = {
                "member_id": member_id,
                "tg_user_id": tg_user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "origin": origin,
            }
            miniapp_url = f"{origin}/#miniapp?tg_token={session_token}&mid={member_id}"
            return {
                "ok": True,
                "bot_username": self._bot_username,
                "miniapp_url": miniapp_url,
                "session_token": session_token,
                "status": "READY_FOR_TELEGRAM",
            }

    def get_session(self, token: str) -> dict[str, Any] | None:
        with self._lock:
            return self._sessions.get(token)

    def format_start_command(self, member_id: str) -> dict[str, Any]:
        return {
            "ok": True,
            "command": "/start",
            "description": "Launch Lunaland Mini-App",
            "reply_markup": {
                "inline_keyboard": [[{
                    "text": " Play Lunaland",
                    "web_app": {"url": f"https://zluna.zeaz.dev/#miniapp?mid={member_id}"},
                }]]
            },
        }

    def format_game_result_message(self, game_name: str, outcome: str, multiplier: float, payout: float, currency: str) -> str:
        if outcome == "win":
            return f" You won {payout:,.0f} {currency} ({multiplier}x) on {game_name}!"
        return f" {game_name} - {multiplier}x ({payout:,.0f} {currency})"

    def format_balance_message(self, balance_lc: int, balance_sc: float, vip_tier: str) -> str:
        return f" Your Lunaland Balance:\n\n {balance_lc:,} Luna Coins (LC)\n {balance_sc:,.2f} Sweeps Coins (SC)\n\n VIP: {vip_tier}"


class DiscordBot:
    """Discord Bot interface for Lunaland."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._bot_name = "LunalandBot"
        self._connected = False
        self._guilds: dict[str, dict[str, Any]] = {}
        self._webhook_url = ""

    def connect(self, bot_token: str) -> dict[str, Any]:
        with self._lock:
            if not bot_token or len(bot_token) < 20:
                return {"ok": False, "error": "invalid bot token"}
            self._connected = True
            return {"ok": True, "bot_name": self._bot_name, "status": "connected"}

    def disconnect(self) -> dict[str, Any]:
        with self._lock:
            self._connected = False
            return {"ok": True, "status": "disconnected"}

    @property
    def is_connected(self) -> bool:
        return self._connected

    def format_slash_command_menu(self) -> dict[str, Any]:
        return {
            "ok": True,
            "commands": [
                {"name": "play", "description": "Launch Lunaland game", "options": [{"name": "game", "description": "Game to play", "type": 3, "required": False}]},
                {"name": "balance", "description": "Check your LC and SC balance"},
                {"name": "spin", "description": "Quick spin on slots", "options": [{"name": "bet", "description": "Bet amount", "type": 4, "required": False}]},
                {"name": "leaderboard", "description": "View top players"},
                {"name": "deposit", "description": "Deposit crypto"},
                {"name": "daily", "description": "Claim daily bonus"},
                {"name": "vip", "description": "Check VIP status"},
            ],
        }

    def format_embed(self, title: str, description: str, fields: list[dict[str, str]], color: int = 0x8B5CF6) -> dict[str, Any]:
        return {
            "ok": True,
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "fields": fields,
                "footer": {"text": "ZLUNA Lunaland Enterprise"},
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }],
        }

    def format_big_win_alert(self, player_name: str, game_name: str, multiplier: float, payout: float, currency: str = "LC") -> dict[str, Any]:
        return self.format_embed(
            title=f" BIG WIN ALERT: {multiplier}x on {game_name}!",
            description=f"**{player_name}** just hit a cosmic payout of **{payout:,.0f} {currency}** at Lunaland!",
            fields=[
                {"name": "Multiplier", "value": f"{multiplier}x", "inline": True},
                {"name": "Payout", "value": f"{payout:,.0f} {currency}", "inline": True},
                {"name": "Provably Fair", "value": "SHA-256 Verified", "inline": True},
            ],
            color=0xFBBF24 if currency == "LC" else 0x10B981,
        )

    def format_balance_embed(self, username: str, balance_lc: int, balance_sc: float, vip_tier: str) -> dict[str, Any]:
        return self.format_embed(
            title=f" {username}'s Lunaland Wallet",
            description=f"**{balance_lc:,}** Luna Coins (LC)\n**{balance_sc:,.2f}** Sweeps Coins (SC)",
            fields=[
                {"name": "VIP Tier", "value": vip_tier, "inline": True},
                {"name": "Status", "value": "Active", "inline": True},
            ],
            color=0x10B981,
        )

    def format_leaderboard_embed(self, top_players: list[dict[str, Any]]) -> dict[str, Any]:
        description = ""
        for i, player in enumerate(top_players[:10], 1):
            medal = {1: "", 2: "", 3: ""}.get(i, f"{i}.")
            description += f"{medal} **{player['name']}** - {player['winnings']:,} LC\n"
        return self.format_embed(
            title=" Lunaland Leaderboard",
            description=description or "No players yet. Be the first!",
            fields=[],
            color=0x8B5CF6,
        )

    def set_webhook(self, webhook_url: str) -> dict[str, Any]:
        with self._lock:
            self._webhook_url = webhook_url
            return {"ok": True, "webhook_url": webhook_url, "status": "configured"}


class BotIntegrationHub:
    """Unified hub for Telegram and Discord bot integrations."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.telegram = TelegramMiniApp()
        self.discord = DiscordBot()
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
        return self.discord.format_big_win_alert(player_name, game_name, multiplier, payout, currency)

    def get_bot_status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "telegram": {
                "bot_username": self._bot_username,
                "status": "ready",
                "miniapp_url": "https://zluna.zeaz.dev/#miniapp",
            },
            "discord": {
                "bot_name": self.discord._bot_name,
                "connected": self.discord.is_connected,
                "commands": 7,
            },
        }


bot_hub = BotIntegrationHub()
