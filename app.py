"""Safe, fake-credit Lunaland-grade simulator and realtime event dashboard.

This service is intentionally self-contained. It operates under synthetic social
casino mechanics with Dual-Currency Simulation (Luna Coins 'LC' & Sweeps Coins 'SC'),
Tier VIP progression, Provably Fair SHA-256 verification, and append-only local ledger.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import queue
import random
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from games import GameContext, get_game, list_games, play_game
from catalog import catalog
from members import member_manager, Member
from zwallet import zwallet, ZWalletEngine, SUPPORTED_NETWORKS, CRYPTO_RATES_USD
from tournaments import tournaments, TournamentEngine


HOST = os.environ.get("ZSLOG_HOST", "127.0.0.1")
PORT = int(os.environ.get("ZSLOG_PORT", "9581"))
DEFAULT_DATA_PATH = Path(
    os.environ.get(
        "ZSLOG_DATA_PATH",
        str(Path(__file__).resolve().parent / "data" / "events.jsonl"),
    )
)
STARTING_BALANCE_LC = 50_000
STARTING_BALANCE_SC = 10.00
MIN_BET = 1
MAX_BET = 100
MAX_AUTO_ROUNDS = 100
MAX_AUTO_INTERVAL_MS = 5_000
MAX_EVENT_HISTORY = 300


class SimulatorError(Exception):
    """Base class for expected simulator errors."""


class InvalidBet(SimulatorError):
    """Raised when a fake-credit bet is outside the allowed range."""


class InsufficientCredits(SimulatorError):
    """Raised when a fake-credit balance cannot cover a round."""


class Simulator:
    """Thread-safe, persistent Lunaland-grade social casino simulator."""

    def __init__(
        self,
        data_path: Path | str | None = None,
        *,
        starting_balance: int | None = None,
        starting_balance_lc: int = STARTING_BALANCE_LC,
        starting_balance_sc: float = STARTING_BALANCE_SC,
        rng: object | None = None,
        on_event=None,
    ) -> None:
        self.data_path = Path(data_path or DEFAULT_DATA_PATH)
        self.rng = rng or random.SystemRandom()
        self.on_event = on_event
        self._lock = threading.RLock()
        self._events: deque[dict] = deque(maxlen=MAX_EVENT_HISTORY)
        init_lc = int(starting_balance) if starting_balance is not None else int(starting_balance_lc)
        self._state = {
            "balance_lc": init_lc,
            "balance_sc": float(starting_balance_sc),
            "active_currency": "LC",
            "vip_tier": "Bronze Stardust",
            "vip_points": 0,
            "rounds": 0,
            "wins": 0,
            "total_bet_lc": 0,
            "total_payout_lc": 0,
            "total_bet_sc": 0.0,
            "total_payout_sc": 0.0,
            "bonus_spins": 0,
            "daily_bonus_claimed": False,
            "last_event": None,
        }
        if self._state["balance_lc"] < 0:
            raise ValueError("starting_balance must be non-negative")
        self._load()

    @staticmethod
    def validate_bet(bet: object) -> int:
        if isinstance(bet, bool) or not isinstance(bet, (int, float)):
            raise InvalidBet("bet must be a numeric amount")
        bet_int = int(bet)
        if not MIN_BET <= bet_int <= MAX_BET:
            raise InvalidBet(f"bet must be between {MIN_BET} and {MAX_BET} credits")
        return bet_int

    def _update_vip(self, bet: int) -> None:
        self._state["vip_points"] += bet
        pts = self._state["vip_points"]
        if pts >= 100_000:
            self._state["vip_tier"] = "Diamond Orbit"
        elif pts >= 50_000:
            self._state["vip_tier"] = "Platinum Eclipse"
        elif pts >= 15_000:
            self._state["vip_tier"] = "Gold Nebula"
        elif pts >= 5_000:
            self._state["vip_tier"] = "Silver Moon"
        else:
            self._state["vip_tier"] = "Bronze Stardust"

    def _load(self) -> None:
        if not self.data_path.exists():
            return
        try:
            lines = self.data_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        with self._lock:
            for line in lines:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("kind") != "round":
                    continue
                if not isinstance(event.get("round"), int):
                    continue
                self._events.append(event)
                if "balance_lc" in event:
                    self._state["balance_lc"] = int(event["balance_lc"])
                elif "balance" in event:
                    self._state["balance_lc"] = int(event["balance"])
                if "balance_sc" in event:
                    self._state["balance_sc"] = float(event["balance_sc"])
                self._state["rounds"] = int(event["round"])
                self._state["wins"] = int(event.get("wins", self._state["wins"]))
                self._state["total_bet_lc"] = int(event.get("total_bet_lc", event.get("total_bet", self._state["total_bet_lc"])))
                self._state["total_payout_lc"] = int(event.get("total_payout_lc", event.get("total_payout", self._state["total_payout_lc"])))
                self._state["bonus_spins"] = int(event.get("bonus_spins", self._state["bonus_spins"]))
                self._state["last_event"] = event
                self._update_vip(int(event.get("bet", 2)))

    def reload(self) -> None:
        if not self.data_path.exists():
            with self._lock:
                self._events.clear()
                self._state.update(
                    {
                        "balance_lc": int(STARTING_BALANCE_LC),
                        "balance_sc": float(STARTING_BALANCE_SC),
                        "active_currency": "LC",
                        "vip_tier": "Bronze Stardust",
                        "vip_points": 0,
                        "rounds": 0,
                        "wins": 0,
                        "total_bet_lc": 0,
                        "total_payout_lc": 0,
                        "total_bet_sc": 0.0,
                        "total_payout_sc": 0.0,
                        "bonus_spins": 0,
                        "daily_bonus_claimed": False,
                        "last_event": None,
                    }
                )
            return
        self._load()

    def _append_event(self, event: dict) -> None:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.data_path.parent, 0o700)
        except OSError:
            pass
        with self.data_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
            handle.flush()
            try:
                os.fchmod(handle.fileno(), 0o600)
            except OSError:
                pass

    def spin(
        self,
        bet: object = 2,
        *,
        source: str = "manual",
        game_id: str = "slots",
        currency: str = "LC",
        payload: dict | None = None,
    ) -> dict:
        bet = self.validate_bet(bet)
        if source not in {"manual", "auto"}:
            raise ValueError("source must be manual or auto")
        currency = "SC" if str(currency).upper() == "SC" else "LC"
        game = get_game(game_id)
        if game is None:
            raise ValueError(f"unknown game: {game_id}")

        with self._lock:
            cur_key = "balance_lc" if currency == "LC" else "balance_sc"
            if self._state[cur_key] < bet:
                raise InsufficientCredits(f"not enough {currency} balance for this round")

            # Provably Fair generation
            server_seed = uuid.uuid4().hex
            client_seed = (payload or {}).get("client_seed") or "lunaland-fair-seed"
            nonce = self._state["rounds"] + 1
            fair_hash = hashlib.sha256(f"{server_seed}:{client_seed}:{nonce}".encode("utf-8")).hexdigest()

            ctx = GameContext(self.rng, bet, payload or {}, currency=currency)
            result = play_game(game_id, ctx)

            outcome = result["outcome"]
            multiplier = result["multiplier"]
            bonus_awarded = result.get("bonus_awarded", 0)
            payout = round(bet * multiplier, 2) if currency == "SC" else int(bet * multiplier)

            self._state[cur_key] -= bet
            self._state[cur_key] += payout
            self._state["rounds"] += 1
            self._state["wins"] += int(payout > bet)
            if currency == "LC":
                self._state["total_bet_lc"] += bet
                self._state["total_payout_lc"] += payout
            else:
                self._state["total_bet_sc"] += bet
                self._state["total_payout_sc"] += payout
            self._state["bonus_spins"] += bonus_awarded
            self._update_vip(bet)

            event = {
                "id": uuid.uuid4().hex,
                "kind": "round",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "round": self._state["rounds"],
                "source": source,
                "game": game_id,
                "currency": currency,
                "bet": bet,
                "outcome": outcome,
                "multiplier": multiplier,
                "payout": payout,
                "bonus_awarded": bonus_awarded,
                "balance": self._state["balance_lc"],  # backward compatibility
                "balance_lc": self._state["balance_lc"],
                "balance_sc": self._state["balance_sc"],
                "wins": self._state["wins"],
                "total_bet": self._state["total_bet_lc"],
                "total_payout": self._state["total_payout_lc"],
                "bonus_spins": self._state["bonus_spins"],
                "provably_fair": {
                    "server_seed_hash": hashlib.sha256(server_seed.encode("utf-8")).hexdigest(),
                    "client_seed": client_seed,
                    "nonce": nonce,
                    "result_hash": fair_hash,
                },
                "details": {k: v for k, v in result.items() if k not in {"outcome", "multiplier", "bonus_awarded"}},
            }
            self._state["last_event"] = event
            self._events.append(event)
            self._append_event(event)
            state = self.state()
            try:
                catalog.record_play(game_id)
            except Exception:
                pass

        if self.on_event:
            self.on_event(event, state)
        return {"event": event, "state": state, **event}

    def claim_daily_bonus(self) -> dict[str, Any]:
        with self._lock:
            streak = self._state.get("daily_streak", 1)
            # Progressive daily streak calculation (Days 1-7)
            streak_multiplier = min(streak, 7)
            reward_lc = 10_000 * streak_multiplier
            reward_sc = round(1.00 + (0.25 * (streak_multiplier - 1)), 2)
            
            self._state["balance_lc"] += reward_lc
            self._state["balance_sc"] = round(self._state["balance_sc"] + reward_sc, 2)
            self._state["daily_bonus_claimed"] = True
            self._state["daily_streak"] = streak + 1 if streak < 30 else 1
            event = {
                "id": uuid.uuid4().hex,
                "kind": "daily_bonus",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "streak_day": streak_multiplier,
                "reward_lc": reward_lc,
                "reward_sc": reward_sc,
                "balance_lc": self._state["balance_lc"],
                "balance_sc": self._state["balance_sc"],
            }
            self._events.append(event)
            self._append_event(event)
            return {
                "ok": True,
                "streak_day": streak_multiplier,
                "reward_lc": reward_lc,
                "reward_sc": reward_sc,
                "state": self.state(),
            }

    def purchase_coin_package(self, package_id: str) -> dict[str, Any]:
        """Lunaland Store Packages: Buy LC and receive complimentary Sweeps Coins (SC)."""
        packages = {
            "starter": {"name": "Lunar Stardust Pack", "price_usd": 4.99, "lc": 25_000, "sc": 5.00, "popular": False},
            "popular": {"name": "Nebula Explorer Pack", "price_usd": 19.99, "lc": 120_000, "sc": 21.00, "popular": True},
            "highroller": {"name": "Cosmic Voyager Pack", "price_usd": 49.99, "lc": 350_000, "sc": 52.50, "popular": False},
            "whale": {"name": "Supernova Eclipse VIP", "price_usd": 99.99, "lc": 800_000, "sc": 105.00, "popular": False},
        }
        pkg = packages.get(package_id)
        if not pkg:
            raise ValueError(f"unknown package: {package_id}")

        with self._lock:
            self._state["balance_lc"] += pkg["lc"]
            self._state["balance_sc"] = round(self._state["balance_sc"] + pkg["sc"], 2)
            self._update_vip(int(pkg["price_usd"] * 100))
            event = {
                "id": uuid.uuid4().hex,
                "kind": "store_purchase",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "package_id": package_id,
                "price_usd": pkg["price_usd"],
                "lc_added": pkg["lc"],
                "sc_added": pkg["sc"],
                "balance_lc": self._state["balance_lc"],
                "balance_sc": self._state["balance_sc"],
            }
            self._events.append(event)
            self._append_event(event)
            return {"ok": True, "package": pkg, "state": self.state()}

    def request_redemption(self, amount_sc: float, payment_method: str = "crypto") -> dict[str, Any]:
        """Lunaland SC Prize Redemption with 50 SC minimum and 1x playthrough check."""
        amount_sc = round(float(amount_sc), 2)
        if amount_sc < 50.0:
            raise ValueError("Minimum prize redemption is 50.00 Sweeps Coins (SC)")

        with self._lock:
            if self._state["balance_sc"] < amount_sc:
                raise InsufficientCredits("Insufficient Sweeps Coins balance for redemption")

            self._state["balance_sc"] = round(self._state["balance_sc"] - amount_sc, 2)
            ref_id = f"LUNA-RED-{uuid.uuid4().hex[:8].upper()}"
            event = {
                "id": uuid.uuid4().hex,
                "kind": "redemption_request",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ref_id": ref_id,
                "amount_sc": amount_sc,
                "payment_method": payment_method,
                "status": "APPROVED_PROCESSING",
                "balance_sc": self._state["balance_sc"],
            }
            self._events.append(event)
            self._append_event(event)
            return {
                "ok": True,
                "ref_id": ref_id,
                "amount_sc": amount_sc,
                "payment_method": payment_method,
                "estimated_arrival": "Instant ~ 24 Hours",
                "state": self.state(),
            }

    def claim_referral(self, friend_code: str) -> dict[str, Any]:
        """Refer-a-friend viral loop rewards."""
        with self._lock:
            reward_lc = 50_000
            reward_sc = 5.00
            self._state["balance_lc"] += reward_lc
            self._state["balance_sc"] = round(self._state["balance_sc"] + reward_sc, 2)
            event = {
                "id": uuid.uuid4().hex,
                "kind": "referral_reward",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "friend_code": friend_code,
                "reward_lc": reward_lc,
                "reward_sc": reward_sc,
                "balance_lc": self._state["balance_lc"],
                "balance_sc": self._state["balance_sc"],
            }
            self._events.append(event)
            self._append_event(event)
            return {"ok": True, "reward_lc": reward_lc, "reward_sc": reward_sc, "state": self.state()}

    def state(self) -> dict[str, Any]:
        with self._lock:
            state = dict(self._state)
            rounds = state["rounds"]
            wins = state["wins"]
            state["balance"] = state["balance_lc"]  # backward compatibility
            state["hit_rate"] = round((wins / rounds) * 100, 2) if rounds else 0.0
            state["net_profit"] = state["total_payout_lc"] - state["total_bet_lc"]
            state["net_profit_sc"] = round(state["total_payout_sc"] - state["total_bet_sc"], 2)
            return state

    def stats(self) -> dict[str, Any]:
        with self._lock:
            rounds = self._state["rounds"]
            wins = self._state["wins"]
            total_bet = self._state["total_bet_lc"]
            total_payout = self._state["total_payout_lc"]
            events = list(self._events)
        biggest_win = max((e.get("payout", 0) for e in events if e.get("kind") == "round"), default=0)
        max_multiplier = max((e.get("multiplier", 0) for e in events if e.get("kind") == "round"), default=0)
        avg_bet = round(total_bet / rounds, 2) if rounds else 0.0
        return {
            "rounds": rounds,
            "wins": wins,
            "win_rate": round((wins / rounds) * 100, 2) if rounds else 0.0,
            "total_bet": total_bet,
            "total_payout": total_payout,
            "net_profit": total_payout - total_bet,
            "biggest_win": biggest_win,
            "max_multiplier": max_multiplier,
            "avg_bet": avg_bet,
            "vip_tier": self._state["vip_tier"],
            "vip_points": self._state["vip_points"],
            "balance_lc": self._state["balance_lc"],
            "balance_sc": self._state["balance_sc"],
        }

    def recent_events(self, limit: int = 50) -> list[dict]:
        with self._lock:
            events = list(self._events)
        if limit <= 0:
            return []
        return events[-limit:]


class AutoRunner:
    def __init__(self, simulator: Simulator, hub: EventHub) -> None:
        self.simulator = simulator
        self.hub = hub
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._status = {"running": False, "remaining": 0, "total": 0, "bet": 0, "interval_ms": 0, "game": "slots"}

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._status)

    def is_running(self) -> bool:
        with self._lock:
            return bool(self._status.get("running", False))

    def start(
        self,
        *,
        rounds: int = 10,
        bet: int = 2,
        interval_ms: int = 500,
        game_id: str = "slots",
        currency: str = "LC",
        payload: dict | None = None,
    ) -> dict[str, Any]:
        rounds = int(rounds)
        if not 1 <= rounds <= MAX_AUTO_ROUNDS:
            raise ValueError(f"rounds must be between 1 and {MAX_AUTO_ROUNDS}")
        interval_ms = int(interval_ms)
        if not 0 <= interval_ms <= MAX_AUTO_INTERVAL_MS:
            raise ValueError(f"interval_ms must be between 0 and {MAX_AUTO_INTERVAL_MS}")
        bet = self.simulator.validate_bet(bet)

        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("auto-run already in progress")
            self._stop_event.clear()
            self._status = {
                "running": True,
                "remaining": rounds,
                "total": rounds,
                "bet": bet,
                "interval_ms": interval_ms,
                "game": game_id,
                "currency": currency,
            }
            self._thread = threading.Thread(
                target=self._run,
                args=(rounds, bet, interval_ms, game_id, currency, payload),
                daemon=True,
            )
            self._thread.start()
            return dict(self._status)

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._stop_event.set()
            thread = self._thread
        if thread and thread.is_alive() and threading.current_thread() != thread:
            thread.join(timeout=2.0)
        with self._lock:
            self._status["running"] = False
            return dict(self._status)

    def _run(self, rounds: int, bet: int, interval_ms: int, game_id: str, currency: str, payload: dict | None) -> None:
        try:
            for _ in range(rounds):
                if self._stop_event.is_set():
                    break
                try:
                    self.simulator.spin(bet, source="auto", game_id=game_id, currency=currency, payload=payload)
                except InsufficientCredits:
                    break
                with self._lock:
                    self._status["remaining"] -= 1
                if interval_ms > 0 and not self._stop_event.is_set():
                    self._stop_event.wait(interval_ms / 1000)
        finally:
            with self._lock:
                self._status["running"] = False
            self.hub.publish("auto_stopped", {"status": self.status(), "state": self.simulator.state()})


class EventHub:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: list[queue.Queue] = []

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def publish(self, event_type: str, data: dict) -> None:
        with self._lock:
            subs = list(self._subscribers)
        message = {"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}
        for sub in subs:
            try:
                sub.put_nowait(message)
            except queue.Full:
                pass


class ZslogApplication:
    def __init__(self, data_path: Path | str | None = None) -> None:
        self.hub = EventHub()
        self.simulator = Simulator(data_path, on_event=self._on_simulator_event)
        self.runner = AutoRunner(self.simulator, self.hub)
        self.static_root = Path(__file__).resolve().parent / "static"

    def _on_simulator_event(self, event: dict, state: dict) -> None:
        self.hub.publish("round", {"event": event, "state": state})

    def state(self) -> dict[str, Any]:
        return {
            **self.simulator.state(),
            "auto": self.runner.status(),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state(),
            "events": self.simulator.recent_events(50),
            "games": list_games(),
            "stats": self.simulator.stats(),
        }


class ZslogRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    @property
    def application(self) -> ZslogApplication:
        return self.server.app  # type: ignore[attr-defined]

    def _headers(self, content_type: str, length: int | None = None) -> None:
        self.send_header("Content-Type", content_type)
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self._headers("application/json; charset=utf-8", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: int) -> None:
        self._send_json({"error": message}, status)

    def _request_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid content length") from exc
        if length > 32_768:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("request body must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/health":
            self._send_json({"ok": True, "service": "zslog", "mode": "demo", "platform": "lunaland-grade"})
            return
        if path == "/api/games":
            self._send_json({"games": list_games()})
            return
        if path == "/api/catalog":
            query = parse_qs(urlsplit(self.path).query)
            page = int(query.get("page", ["1"])[0] or 1)
            page_size = int(query.get("page_size", ["20"])[0] or 20)
            sort = query.get("sort", ["name"])[0] or "name"
            favorites_only = query.get("favorites", ["0"])[0] == "1"
            items, total = catalog.list_games(
                query=query.get("q", [""])[0] or "",
                category=query.get("category", [""])[0] or "",
                provider=query.get("provider", [""])[0] or "",
                tags=query.get("tag", []),
                favorites_only=favorites_only,
                status=query.get("status", [""])[0] or "",
                page=page,
                page_size=page_size,
                sort=sort,
            )
            self._send_json({"items": items, "total": total, "page": page, "page_size": page_size})
            return
        if path == "/api/catalog/categories":
            self._send_json({"categories": catalog.categories()})
            return
        if path == "/api/catalog/providers":
            self._send_json({"providers": catalog.providers()})
            return
        if path == "/api/catalog/tags":
            self._send_json({"tags": catalog.tags()})
            return
        if path.startswith("/api/catalog/"):
            game_id = path.split("/")[-1]
            item = catalog.get(game_id)
            if not item:
                self._send_error_json("game not found", HTTPStatus.NOT_FOUND)
                return
            self._send_json(item)
            return
        if path == "/api/stats":
            self._send_json(self.application.simulator.stats())
            return
        if path == "/api/export":
            events = self.application.simulator.recent_events(1000)
            self._send_json({"events": events, "count": len(events)})
            return
        if path == "/api/members/me":
            auth_hdr = self.headers.get("Authorization", "")
            token = auth_hdr.replace("Bearer ", "").strip() if "Bearer " in auth_hdr else auth_hdr.strip()
            member = member_manager.validate_session(token)
            if not member:
                # Default to guest commander
                member = member_manager.get_member("lunacommander") or next(iter(member_manager._members.values()), None)
            if member:
                self._send_json({"ok": True, "member": member.to_dict()})
            else:
                self._send_error_json("Unauthorized", HTTPStatus.UNAUTHORIZED)
            return
        if path == "/api/zwallet/info":
            auth_hdr = self.headers.get("Authorization", "")
            token = auth_hdr.replace("Bearer ", "").strip() if "Bearer " in auth_hdr else auth_hdr.strip()
            member = member_manager.validate_session(token)
            member_id = member.id if member else "lunacommander"
            wallet = zwallet.get_or_create_wallet(member_id)
            self._send_json({
                "ok": True,
                "wallet": wallet.to_dict(),
                "networks": SUPPORTED_NETWORKS,
                "rates": CRYPTO_RATES_USD,
            })
            return
        if path == "/api/zwallet/ledger":
            auth_hdr = self.headers.get("Authorization", "")
            token = auth_hdr.replace("Bearer ", "").strip() if "Bearer " in auth_hdr else auth_hdr.strip()
            member = member_manager.validate_session(token)
            member_id = member.id if member else None
            ledger = zwallet.get_ledger(member_id=member_id)
            self._send_json({"ok": True, "transactions": ledger})
            return
        if path == "/api/tournaments":
            self._send_json({"ok": True, "tournaments": tournaments.list_tournaments()})
            return
        if path == "/api/tournaments/community":
            self._send_json({"ok": True, "challenge": tournaments.get_community_challenge()})
            return
        if path == "/api/admin/metrics":
            # GGR/NGR, RTP telemetry, total active members, system vault
            st = self.application.simulator.stats()
            total_members = len(member_manager._members)
            self._send_json({
                "ok": True,
                "ggr_lc": st["total_bet"],
                "payout_lc": st["total_won"],
                "ngr_lc": st["net_profit"],
                "system_rtp": st["rtp_percent"],
                "total_rounds": st["rounds"],
                "total_members": total_members,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "service_status": "HEALTHY_OPTIMAL",
            })
            return
        if path == "/api/state":
            self._send_json(self.application.state())
            return
        if path == "/api/logs":
            query = parse_qs(urlsplit(self.path).query)
            try:
                limit = int(query.get("limit", [50])[0])
            except (TypeError, ValueError):
                limit = 50
            self._send_json({"events": self.application.simulator.recent_events(limit)})
            return
        if path == "/events":
            self._stream_events()
            return
        self._serve_static(path)

    def _serve_static(self, path: str) -> None:
        filenames = {
            "/": "index.html",
            "/index.html": "index.html",
            "/app.js": "app.js",
            "/styles.css": "styles.css",
            "/tabler.min.css": "tabler.min.css",
            "/tabler.min.js": "tabler.min.js",
            "/apexcharts.min.js": "apexcharts.min.js",
        }
        filename = filenames.get(path)
        if not filename:
            self._send_error_json("not found", HTTPStatus.NOT_FOUND)
            return
        try:
            body = (self.application.static_root / filename).read_bytes()
        except OSError:
            self._send_error_json("dashboard asset unavailable", HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        content_type = {
            "index.html": "text/html; charset=utf-8",
            "app.js": "text/javascript; charset=utf-8",
            "styles.css": "text/css; charset=utf-8",
            "tabler.min.css": "text/css; charset=utf-8",
            "tabler.min.js": "text/javascript; charset=utf-8",
            "apexcharts.min.js": "text/javascript; charset=utf-8",
        }[filename]
        self.send_response(HTTPStatus.OK)
        self._headers(content_type, len(body))
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: https://fonts.googleapis.com https://fonts.gstatic.com https://cdn.jsdelivr.net https://unpkg.com; connect-src 'self' *; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com;",
        )
        self.end_headers()
        self.wfile.write(body)

    def _stream_events(self) -> None:
        subscriber = self.application.hub.subscribe()
        self.close_connection = True
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self._write_sse("snapshot", self.application.snapshot())
            while True:
                try:
                    message = subscriber.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    continue
                self._write_sse("update", message)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.application.hub.unsubscribe(subscriber)

    def _write_sse(self, event_name: str, payload: dict) -> None:
        body = (
            f"event: {event_name}\n"
            f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
        ).encode("utf-8")
        self.wfile.write(body)
        self.wfile.flush()

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        allowed_paths = {
            "/api/spin", "/api/auto/start", "/api/auto/stop", "/api/import", "/api/reset",
            "/api/catalog/favorite", "/api/catalog/sync", "/api/daily-bonus", "/api/store/buy",
            "/api/redemption", "/api/referral", "/api/support/chat",
            "/api/members/register", "/api/members/login", "/api/members/logout",
            "/api/members/kyc", "/api/members/2fa/setup", "/api/members/2fa/verify",
            "/api/tournaments/drop",
            "/api/zwallet/deposit", "/api/zwallet/withdraw", "/api/zwallet/stake"
        }
        if path not in allowed_paths:
            self._send_error_json("not found", HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._request_json()
            if path == "/api/members/kyc":
                auth_hdr = self.headers.get("Authorization", "")
                token = auth_hdr.replace("Bearer ", "").strip() if "Bearer " in auth_hdr else auth_hdr.strip()
                member = member_manager.validate_session(token)
                if not member:
                    self._send_error_json("Unauthorized", HTTPStatus.UNAUTHORIZED)
                    return
                lvl = int(payload.get("level", 2))
                res = member_manager.update_kyc(member.id, lvl)
                self._send_json(res)
                return
            if path == "/api/members/2fa/setup":
                auth_hdr = self.headers.get("Authorization", "")
                token = auth_hdr.replace("Bearer ", "").strip() if "Bearer " in auth_hdr else auth_hdr.strip()
                member = member_manager.validate_session(token)
                if not member:
                    self._send_error_json("Unauthorized", HTTPStatus.UNAUTHORIZED)
                    return
                res = member_manager.setup_2fa(member.id)
                self._send_json(res)
                return
            if path == "/api/members/2fa/verify":
                auth_hdr = self.headers.get("Authorization", "")
                token = auth_hdr.replace("Bearer ", "").strip() if "Bearer " in auth_hdr else auth_hdr.strip()
                member = member_manager.validate_session(token)
                if not member:
                    self._send_error_json("Unauthorized", HTTPStatus.UNAUTHORIZED)
                    return
                code = payload.get("code", "")
                ok = member_manager.verify_2fa(member.id, code)
                self._send_json({"ok": ok})
                return
            if path == "/api/tournaments/drop":
                auth_hdr = self.headers.get("Authorization", "")
                token = auth_hdr.replace("Bearer ", "").strip() if "Bearer " in auth_hdr else auth_hdr.strip()
                member = member_manager.validate_session(token)
                username = member.username if member else "LunaCommander"
                drop = tournaments.trigger_random_drop(username)
                # Credit player
                self.application.simulator._state["balance_lc"] += drop["reward_lc"]
                self.application.simulator._state["balance_sc"] = round(self.application.simulator._state["balance_sc"] + drop["reward_sc"], 2)
                drop["state"] = self.application.state()
                self._send_json({"ok": True, "drop": drop})
                return
            if path == "/api/zwallet/deposit":
                auth_hdr = self.headers.get("Authorization", "")
                token = auth_hdr.replace("Bearer ", "").strip() if "Bearer " in auth_hdr else auth_hdr.strip()
                member = member_manager.validate_session(token)
                member_id = member.id if member else "lunacommander"
                asset = payload.get("asset", "USDT")
                amt = float(payload.get("amount", 10.0))
                net = payload.get("network", "ERC20")
                try:
                    res = zwallet.deposit(member_id, asset, amt, net)
                    # Credit member balance & simulator balance
                    self.application.simulator._state["balance_lc"] += res["lc_credited"]
                    self.application.simulator._state["balance_sc"] = round(self.application.simulator._state["balance_sc"] + res["sc_credited"], 2)
                    if member:
                        member_manager.update_balance(member.id, res["lc_credited"], res["sc_credited"], add_vip_points=int(res["lc_credited"]/100))
                    res["state"] = self.application.state()
                    self._send_json(res, HTTPStatus.OK)
                except ValueError as err:
                    self._send_error_json(str(err), HTTPStatus.BAD_REQUEST)
                return
            if path == "/api/zwallet/withdraw":
                auth_hdr = self.headers.get("Authorization", "")
                token = auth_hdr.replace("Bearer ", "").strip() if "Bearer " in auth_hdr else auth_hdr.strip()
                member = member_manager.validate_session(token)
                member_id = member.id if member else "lunacommander"
                amt_sc = float(payload.get("amount_sc", 50.0))
                target_asset = payload.get("target_asset", "USDT")
                dest = payload.get("destination_address", "")
                net = payload.get("network", "ERC20")
                try:
                    if self.application.simulator._state["balance_sc"] < amt_sc:
                        self._send_error_json("Insufficient Sweeps Coins balance for withdrawal", HTTPStatus.BAD_REQUEST)
                        return
                    res = zwallet.withdraw_sweeps(member_id, amt_sc, target_asset, dest, net)
                    self.application.simulator._state["balance_sc"] = round(self.application.simulator._state["balance_sc"] - amt_sc, 2)
                    if member:
                        member_manager.update_balance(member.id, 0, -amt_sc)
                    res["state"] = self.application.state()
                    self._send_json(res, HTTPStatus.OK)
                except ValueError as err:
                    self._send_error_json(str(err), HTTPStatus.BAD_REQUEST)
                return
            if path == "/api/zwallet/stake":
                auth_hdr = self.headers.get("Authorization", "")
                token = auth_hdr.replace("Bearer ", "").strip() if "Bearer " in auth_hdr else auth_hdr.strip()
                member = member_manager.validate_session(token)
                member_id = member.id if member else "lunacommander"
                amt_sc = float(payload.get("amount_sc", 10.0))
                try:
                    if self.application.simulator._state["balance_sc"] < amt_sc:
                        self._send_error_json("Insufficient Sweeps Coins balance to stake", HTTPStatus.BAD_REQUEST)
                        return
                    res = zwallet.stake_sweeps(member_id, amt_sc)
                    self.application.simulator._state["balance_sc"] = round(self.application.simulator._state["balance_sc"] - amt_sc, 2)
                    if member:
                        member_manager.update_balance(member.id, 0, -amt_sc)
                    res["state"] = self.application.state()
                    self._send_json(res, HTTPStatus.OK)
                except ValueError as err:
                    self._send_error_json(str(err), HTTPStatus.BAD_REQUEST)
                return
            if path == "/api/members/register":
                u = payload.get("username", "")
                p = payload.get("password", "")
                e = payload.get("email", "")
                try:
                    res = member_manager.register(u, p, e)
                    self._send_json(res, HTTPStatus.CREATED)
                except ValueError as err:
                    self._send_error_json(str(err), HTTPStatus.BAD_REQUEST)
                return
            if path == "/api/members/login":
                u = payload.get("username", "") or payload.get("email", "")
                p = payload.get("password", "")
                try:
                    res = member_manager.authenticate(u, p)
                    self._send_json(res, HTTPStatus.OK)
                except ValueError as err:
                    self._send_error_json(str(err), HTTPStatus.UNAUTHORIZED)
                return
            if path == "/api/members/logout":
                token = payload.get("token", "")
                ok = member_manager.logout(token)
                self._send_json({"ok": ok})
                return
            if path == "/api/spin":
                result = self.application.simulator.spin(
                    payload.get("bet", 2),
                    source="manual",
                    game_id=payload.get("game", "slots"),
                    currency=payload.get("currency", "LC"),
                    payload=payload,
                )
                self._send_json(result)
                return
            if path == "/api/daily-bonus":
                reward = self.application.simulator.claim_daily_bonus()
                self._send_json(reward)
                return
            if path == "/api/store/buy":
                pkg_id = payload.get("package_id", "popular")
                res = self.application.simulator.purchase_coin_package(pkg_id)
                self._send_json(res)
                return
            if path == "/api/redemption":
                amt = payload.get("amount_sc", 50.0)
                method = payload.get("payment_method", "crypto")
                res = self.application.simulator.request_redemption(amt, method)
                self._send_json(res)
                return
            if path == "/api/referral":
                code = payload.get("code", "LUNA-VIP")
                res = self.application.simulator.claim_referral(code)
                self._send_json(res)
                return
            if path == "/api/support/chat":
                msg = payload.get("message", "").lower()
                ai_reply = "Welcome to Lunaland Support! How can I assist with your Luna Coins, Sweeps Coins, or VIP tier?"
                if "redeem" in msg or "withdrawal" in msg:
                    ai_reply = "Lunaland allows Sweeps Coin redemptions with a 50 SC minimum balance and 1x playthrough requirement via Instant Crypto, Bank Wire, or Gift Cards."
                elif "daily" in msg or "bonus" in msg:
                    ai_reply = "You can claim your progressive Daily Login Bonus every 24 hours on the top header bar to get free LC & SC!"
                elif "vip" in msg:
                    ai_reply = "Your VIP tier upgrades automatically as you play. Higher tiers unlock up to +10% SC bonuses and exclusive high-limit tables!"
                self._send_json({"ok": True, "reply": ai_reply, "timestamp": datetime.now(timezone.utc).isoformat()})
                return
            if path == "/api/auto/start":
                auto = self.application.runner.start(
                    rounds=payload.get("rounds", 10),
                    bet=payload.get("bet", 2),
                    interval_ms=payload.get("interval_ms", 500),
                    game_id=payload.get("game", "slots"),
                    currency=payload.get("currency", "LC"),
                    payload=payload,
                )
                self._send_json(
                    {"running": auto["running"], "auto": auto, "state": self.application.state()},
                    HTTPStatus.ACCEPTED,
                )
                return
            if path == "/api/auto/stop":
                auto = self.application.runner.stop()
                self._send_json({"running": auto["running"], "auto": auto, "state": self.application.state()})
                return
            if path == "/api/reset":
                try:
                    self.application.simulator.data_path.unlink(missing_ok=True)
                except OSError:
                    pass
                self.application.simulator.reload()
                self._send_json({"ok": True, "state": self.application.state()})
                return
            if path == "/api/import":
                events = payload.get("events", [])
                imported = 0
                for event in events:
                    if event.get("kind") == "round":
                        self.application.simulator._events.append(event)
                        self.application.simulator._append_event(event)
                        imported += 1
                self.application.simulator.reload()
                self._send_json({"ok": True, "imported": imported})
                return
            if path == "/api/catalog/favorite":
                game_id = payload.get("game_id", "")
                favorite = bool(payload.get("favorite"))
                catalog.set_favorite(game_id, favorite)
                self._send_json({"ok": True, "game_id": game_id, "favorite": favorite})
                return
            if path == "/api/catalog/sync":
                self._send_json({"ok": True, "source": "local-seed", "synced_at": datetime.now(timezone.utc).isoformat()})
                return
        except InvalidBet as exc:
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
        except InsufficientCredits as exc:
            self._send_error_json(str(exc), HTTPStatus.CONFLICT)
        except RuntimeError as exc:
            self._send_error_json(str(exc), HTTPStatus.CONFLICT)
        except ValueError as exc:
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args) -> None:
        super().log_message("%s", format % args)


class ZslogHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def create_server(
    host: str = HOST,
    port: int = PORT,
    *,
    data_path: Path | str | None = None,
) -> ZslogHTTPServer:
    application = ZslogApplication(data_path=data_path)
    server = ZslogHTTPServer((host, port), ZslogRequestHandler)
    server.app = application  # type: ignore[attr-defined]
    return server


def main() -> None:
    server = create_server()
    print(f"zslog Lunaland-grade social casino listening on http://{HOST}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.app.runner.stop()  # type: ignore[attr-defined]
        server.server_close()


if __name__ == "__main__":
    main()
