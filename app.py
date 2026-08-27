"""Safe, fake-credit simulator and realtime event dashboard.

This service is intentionally self-contained.  It does not connect to a
casino, place bets, control a browser, or handle real currency.  Every round
uses synthetic credits and writes an append-only local event record.
"""

from __future__ import annotations

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


HOST = os.environ.get("ZSLOG_HOST", "127.0.0.1")
PORT = int(os.environ.get("ZSLOG_PORT", "9581"))
DEFAULT_DATA_PATH = Path(
    os.environ.get(
        "ZSLOG_DATA_PATH",
        str(Path(__file__).resolve().parent / "data" / "events.jsonl"),
    )
)
STARTING_BALANCE = 1_000
MIN_BET = 1
MAX_BET = 100
MAX_AUTO_ROUNDS = 100
MAX_AUTO_INTERVAL_MS = 5_000
MAX_EVENT_HISTORY = 200


class SimulatorError(Exception):
    """Base class for expected simulator errors."""


class InvalidBet(SimulatorError):
    """Raised when a fake-credit bet is outside the allowed range."""


class InsufficientCredits(SimulatorError):
    """Raised when a fake-credit balance cannot cover a round."""


class Simulator:
    """Thread-safe, persistent fake-credit round simulator."""

    def __init__(
        self,
        data_path: Path | str | None = None,
        *,
        starting_balance: int = STARTING_BALANCE,
        rng: object | None = None,
        on_event=None,
    ) -> None:
        self.data_path = Path(data_path or DEFAULT_DATA_PATH)
        self.rng = rng or random.SystemRandom()
        self.on_event = on_event
        self._lock = threading.RLock()
        self._events: deque[dict] = deque(maxlen=MAX_EVENT_HISTORY)
        self._state = {
            "balance": int(starting_balance),
            "rounds": 0,
            "wins": 0,
            "total_bet": 0,
            "total_payout": 0,
            "bonus_spins": 0,
            "last_event": None,
        }
        if self._state["balance"] < 0:
            raise ValueError("starting_balance must be non-negative")
        self._load()

    @staticmethod
    def validate_bet(bet: object) -> int:
        if isinstance(bet, bool) or not isinstance(bet, int):
            raise InvalidBet("bet must be an integer fake-credit amount")
        if not MIN_BET <= bet <= MAX_BET:
            raise InvalidBet(f"bet must be between {MIN_BET} and {MAX_BET} credits")
        return bet

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
                self._state["balance"] = int(event["balance"])
                self._state["rounds"] = int(event["round"])
                self._state["wins"] = int(event.get("wins", self._state["wins"]))
                self._state["total_bet"] = int(
                    event.get("total_bet", self._state["total_bet"])
                )
                self._state["total_payout"] = int(
                    event.get("total_payout", self._state["total_payout"])
                )
                self._state["bonus_spins"] = int(
                    event.get("bonus_spins", self._state["bonus_spins"])
                )
                self._state["last_event"] = event

    def reload(self) -> None:
        if not self.data_path.exists():
            with self._lock:
                self._events.clear()
                self._state.update(
                    {
                        "balance": int(STARTING_BALANCE),
                        "rounds": 0,
                        "wins": 0,
                        "total_bet": 0,
                        "total_payout": 0,
                        "bonus_spins": 0,
                        "last_event": None,
                    }
                )
            return
        try:
            lines = self.data_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        with self._lock:
            self._events.clear()
            self._state.update(
                {
                    "balance": int(STARTING_BALANCE),
                    "rounds": 0,
                    "wins": 0,
                    "total_bet": 0,
                    "total_payout": 0,
                    "bonus_spins": 0,
                    "last_event": None,
                }
            )
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
                self._state["balance"] = int(event["balance"])
                self._state["rounds"] = int(event["round"])
                self._state["wins"] = int(event.get("wins", self._state["wins"]))
                self._state["total_bet"] = int(
                    event.get("total_bet", self._state["total_bet"])
                )
                self._state["total_payout"] = int(
                    event.get("total_payout", self._state["total_payout"])
                )
                self._state["bonus_spins"] = int(
                    event.get("bonus_spins", self._state["bonus_spins"])
                )
                self._state["last_event"] = event

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

    def spin(self, bet: object = 2, *, source: str = "manual", game_id: str = "slots", payload: dict | None = None) -> dict:
        bet = self.validate_bet(bet)
        if source not in {"manual", "auto"}:
            raise ValueError("source must be manual or auto")
        game = get_game(game_id)
        if game is None:
            raise ValueError(f"unknown game: {game_id}")

        with self._lock:
            if self._state["balance"] < bet:
                raise InsufficientCredits("not enough fake credits for this round")

            ctx = GameContext(self.rng, bet, payload or {})
            result = play_game(game_id, ctx)

            outcome = result["outcome"]
            multiplier = result["multiplier"]
            bonus_awarded = result["bonus_awarded"]
            payout = bet * multiplier

            self._state["balance"] -= bet
            self._state["balance"] += payout
            self._state["rounds"] += 1
            self._state["wins"] += int(payout > bet)
            self._state["total_bet"] += bet
            self._state["total_payout"] += payout
            self._state["bonus_spins"] += bonus_awarded

            event = {
                "id": uuid.uuid4().hex,
                "kind": "round",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "round": self._state["rounds"],
                "source": source,
                "game": game_id,
                "bet": bet,
                "outcome": outcome,
                "multiplier": multiplier,
                "payout": payout,
                "bonus_awarded": bonus_awarded,
                "balance": self._state["balance"],
                "wins": self._state["wins"],
                "total_bet": self._state["total_bet"],
                "total_payout": self._state["total_payout"],
                "bonus_spins": self._state["bonus_spins"],
                "details": {k: v for k, v in result.items() if k not in {"outcome", "multiplier", "bonus_awarded"}},
            }
            self._state["last_event"] = event
            self._events.append(event)
            self._append_event(event)
            state = self.state()

        if self.on_event:
            self.on_event({"type": "round", "event": event, "state": state})
        return {"event": event, "state": state}

    def state(self) -> dict:
        with self._lock:
            return dict(self._state)

    def recent_events(self, limit: int = 50) -> list[dict]:
        limit = max(1, min(int(limit), MAX_EVENT_HISTORY))
        with self._lock:
            return list(self._events)[-limit:][::-1]

    def stats(self) -> dict:
        with self._lock:
            events = list(self._events)
            if not events:
                return {
                    "rounds": 0,
                    "total_bet": 0,
                    "total_payout": 0,
                    "win_rate": 0,
                    "biggest_win": 0,
                    "biggest_multiplier": 0,
                    "game_breakdown": {},
                    "outcome_breakdown": {},
                    "avg_bet": 0,
                    "net_profit": 0,
                }
            total_bet = sum(e.get("bet", 0) for e in events)
            total_payout = sum(e.get("payout", 0) for e in events)
            wins = [e for e in events if e.get("payout", 0) > 0]
            biggest_win = max((e.get("payout", 0) for e in events), default=0)
            biggest_multiplier = max((e.get("multiplier", 0) for e in events), default=0)
            game_breakdown = {}
            outcome_breakdown = {}
            for e in events:
                g = e.get("game", "unknown")
                o = e.get("outcome", "unknown")
                game_breakdown[g] = game_breakdown.get(g, 0) + 1
                outcome_breakdown[o] = outcome_breakdown.get(o, 0) + 1
            return {
                "rounds": len(events),
                "total_bet": total_bet,
                "total_payout": total_payout,
                "win_rate": round(len(wins) / len(events) * 100, 1) if events else 0,
                "biggest_win": biggest_win,
                "biggest_multiplier": biggest_multiplier,
                "game_breakdown": game_breakdown,
                "outcome_breakdown": outcome_breakdown,
                "avg_bet": round(total_bet / len(events), 1) if events else 0,
                "net_profit": total_payout - total_bet,
            }


class EventHub:
    """Small in-process fan-out hub for server-sent events."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: set[queue.Queue] = set()

    def subscribe(self) -> queue.Queue:
        subscriber: queue.Queue = queue.Queue(maxsize=128)
        with self._lock:
            self._subscribers.add(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)

    def publish(self, message: dict) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(message)
            except queue.Full:
                try:
                    subscriber.get_nowait()
                except queue.Empty:
                    pass
                try:
                    subscriber.put_nowait(message)
                except queue.Full:
                    pass


class AutoRunner:
    """Bounded background runner for synthetic rounds."""

    def __init__(self, simulator: Simulator, on_status=None) -> None:
        self.simulator = simulator
        self.on_status = on_status
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._requested = 0
        self._completed = 0
        self._running = False
        self._game_id = "slots"
        self._payload: dict = {}

    def start(self, rounds: object = 10, bet: object = 2, interval_ms: object = 500, *, game_id: str = "slots", payload: dict | None = None) -> dict:
        if isinstance(rounds, bool) or not isinstance(rounds, int):
            raise ValueError("rounds must be an integer")
        if not 1 <= rounds <= MAX_AUTO_ROUNDS:
            raise ValueError(f"rounds must be between 1 and {MAX_AUTO_ROUNDS}")
        if isinstance(interval_ms, bool) or not isinstance(interval_ms, int):
            raise ValueError("interval_ms must be an integer")
        if not 0 <= interval_ms <= MAX_AUTO_INTERVAL_MS:
            raise ValueError(f"interval_ms must be between 0 and {MAX_AUTO_INTERVAL_MS}")
        bet = Simulator.validate_bet(bet)

        with self._lock:
            if self._running:
                raise RuntimeError("an auto run is already active")
            self._stop = threading.Event()
            self._requested = rounds
            self._completed = 0
            self._running = True
            self._game_id = game_id
            self._payload = payload or {}
            self._thread = threading.Thread(
                target=self._run,
                args=(rounds, bet, interval_ms, game_id, payload or {}),
                daemon=True,
                name="zslog-auto-runner",
            )
            self._thread.start()
            snapshot = self.snapshot()

        self._emit_status("started")
        return snapshot

    def _run(self, rounds: int, bet: int, interval_ms: int, game_id: str, payload: dict) -> None:
        try:
            for _ in range(rounds):
                if self._stop.is_set():
                    break
                try:
                    self.simulator.spin(bet, source="auto", game_id=game_id, payload=payload)
                except InsufficientCredits:
                    break
                with self._lock:
                    self._completed += 1
                if self._stop.wait(interval_ms / 1000):
                    break
        finally:
            with self._lock:
                self._running = False
            self._emit_status("stopped")

    def stop(self) -> dict:
        with self._lock:
            thread = self._thread
            self._stop.set()
        if thread and thread is not threading.current_thread():
            thread.join(timeout=2)
        return self.snapshot()

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "running": self._running,
                "requested": self._requested,
                "completed": self._completed,
            }

    def _emit_status(self, status: str) -> None:
        if self.on_status:
            self.on_status({"type": "auto", "status": status, "auto": self.snapshot()})


class ZslogApplication:
    def __init__(self, data_path: Path | str | None = None) -> None:
        self.hub = EventHub()
        self.simulator = Simulator(data_path=data_path, on_event=self.hub.publish)
        self.runner = AutoRunner(self.simulator, on_status=self.hub.publish)
        self.static_root = Path(__file__).resolve().parent / "static"

    def state(self) -> dict:
        state = self.simulator.state()
        state["auto"] = self.runner.snapshot()
        return state

    def snapshot(self) -> dict:
        return {
            "type": "snapshot",
            "state": self.state(),
            "events": self.simulator.recent_events(50),
        }


class ZslogRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "zslog"
    sys_version = ""

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
        if length > 8_192:
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
            self._send_json({"ok": True, "service": "zslog", "mode": "demo"})
            return
        if path == "/api/games":
            self._send_json({"games": list_games()})
            return
        if path == "/api/stats":
            self._send_json(self.application.simulator.stats())
            return
        if path == "/api/export":
            events = self.application.simulator.recent_events(1000)
            self._send_json({"events": events, "count": len(events)})
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
        filenames = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/styles.css": "styles.css"}
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
        }[filename]
        self.send_response(HTTPStatus.OK)
        self._headers(content_type, len(body))
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self'",
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
        if path not in {"/api/spin", "/api/auto/start", "/api/auto/stop", "/api/import", "/api/reset"}:
            self._send_error_json("not found", HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._request_json()
            if path == "/api/spin":
                result = self.application.simulator.spin(
                    payload.get("bet", 2),
                    source="manual",
                    game_id=payload.get("game", "slots"),
                    payload=payload,
                )
                self._send_json(result)
                return
            if path == "/api/auto/start":
                auto = self.application.runner.start(
                    rounds=payload.get("rounds", 10),
                    bet=payload.get("bet", 2),
                    interval_ms=payload.get("interval_ms", 500),
                    game_id=payload.get("game", "slots"),
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
        except InvalidBet as exc:
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
        except InsufficientCredits as exc:
            self._send_error_json(str(exc), HTTPStatus.CONFLICT)
        except RuntimeError as exc:
            self._send_error_json(str(exc), HTTPStatus.CONFLICT)
        except ValueError as exc:
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args) -> None:
        # Keep service logs useful without leaking request bodies or credentials.
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
    print(f"zslog demo listening on http://{HOST}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.app.runner.stop()  # type: ignore[attr-defined]
        server.server_close()


if __name__ == "__main__":
    main()
