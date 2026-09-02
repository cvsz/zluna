"""WebRTC Ultra-Low Latency Live Dealer Stream Ingestion Engine for ZLUNA.

Implements signaling server, room management, and ICE candidate relay for
direct peer-to-peer video streaming between Live Dealer studios and players.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from typing import Any

from datetime import datetime, timezone


class StreamRoom:
    """Represents a single Live Dealer streaming room."""

    def __init__(self, room_id: str, studio_id: str, game_type: str, max_viewers: int = 100) -> None:
        self.room_id = room_id
        self.studio_id = studio_id
        self.game_type = game_type
        self.max_viewers = max_viewers
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.studio_peer_id: str | None = None
        self.viewers: dict[str, dict[str, Any]] = {}
        self.ice_candidates: dict[str, list[dict[str, Any]]] = {}
        self.sdp_offers: dict[str, dict[str, Any]] = {}
        self.sdp_answers: dict[str, dict[str, Any]] = {}
        self.status = "waiting"
        self.bitrate_kbps = 0
        self.latency_ms = 0

    def to_dict(self, include_sdp: bool = False) -> dict[str, Any]:
        result = {
            "room_id": self.room_id,
            "studio_id": self.studio_id,
            "game_type": self.game_type,
            "status": self.status,
            "viewer_count": len(self.viewers),
            "max_viewers": self.max_viewers,
            "created_at": self.created_at,
            "bitrate_kbps": self.bitrate_kbps,
            "latency_ms": self.latency_ms,
            "has_studio": self.studio_peer_id is not None,
        }
        if include_sdp:
            result["sdp_offers"] = self.sdp_offers
            result["sdp_answers"] = self.sdp_answers
            result["ice_candidates"] = self.ice_candidates
        return result

    def add_viewer(self, peer_id: str, member_id: str) -> bool:
        if len(self.viewers) >= self.max_viewers:
            return False
        self.viewers[peer_id] = {
            "peer_id": peer_id,
            "member_id": member_id,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        return True

    def remove_viewer(self, peer_id: str) -> None:
        self.viewers.pop(peer_id, None)
        self.sdp_offers.pop(peer_id, None)
        self.sdp_answers.pop(peer_id, None)
        self.ice_candidates.pop(peer_id, None)

    def set_studio_peer(self, peer_id: str) -> None:
        self.studio_peer_id = peer_id
        self.status = "live"

    def store_sdp_offer(self, peer_id: str, sdp: dict[str, Any]) -> None:
        self.sdp_offers[peer_id] = {
            "sdp": sdp,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def store_sdp_answer(self, peer_id: str, sdp: dict[str, Any]) -> None:
        self.sdp_answers[peer_id] = {
            "sdp": sdp,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def add_ice_candidate(self, peer_id: str, candidate: dict[str, Any]) -> None:
        if peer_id not in self.ice_candidates:
            self.ice_candidates[peer_id] = []
        self.ice_candidates[peer_id].append({
            "candidate": candidate,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


class WebRTCStreamEngine:
    """Manages WebRTC Live Dealer streaming rooms and signaling."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rooms: dict[str, StreamRoom] = {}
        self._peer_to_room: dict[str, str] = {}
        self._studios: dict[str, dict[str, Any]] = {}
        self._stream_stats: dict[str, dict[str, Any]] = {}

    def register_studio(self, studio_id: str, name: str, location: str = "Monte Carlo") -> dict[str, Any]:
        with self._lock:
            self._studios[studio_id] = {
                "studio_id": studio_id,
                "name": name,
                "location": location,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "active_rooms": 0,
                "total_streams": 0,
                "status": "online",
            }
            return {"ok": True, "studio": self._studios[studio_id]}

    def create_room(self, studio_id: str, game_type: str = "blackjack", max_viewers: int = 100) -> dict[str, Any]:
        with self._lock:
            if studio_id not in self._studios:
                self.register_studio(studio_id, f"Studio {studio_id}")
            room_id = f"room_{secrets.token_hex(8)}"
            room = StreamRoom(room_id, studio_id, game_type, max_viewers)
            self._rooms[room_id] = room
            self._studios[studio_id]["active_rooms"] += 1
            self._studios[studio_id]["total_streams"] += 1
            return {"ok": True, "room": room.to_dict()}

    def get_room(self, room_id: str) -> StreamRoom | None:
        with self._lock:
            return self._rooms.get(room_id)

    def list_rooms(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rooms = list(self._rooms.values())
            if status:
                rooms = [r for r in rooms if r.status == status]
            return [r.to_dict() for r in rooms]

    def list_studios(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._studios.values())

    def studio_join_room(self, room_id: str, peer_id: str) -> dict[str, Any]:
        with self._lock:
            room = self._rooms.get(room_id)
            if not room:
                return {"ok": False, "error": "room not found"}
            if room.studio_peer_id:
                return {"ok": False, "error": "studio already connected"}
            room.set_studio_peer(peer_id)
            self._peer_to_room[peer_id] = room_id
            return {"ok": True, "room": room.to_dict()}

    def viewer_join_room(self, room_id: str, peer_id: str, member_id: str) -> dict[str, Any]:
        with self._lock:
            room = self._rooms.get(room_id)
            if not room:
                return {"ok": False, "error": "room not found"}
            if not room.add_viewer(peer_id, member_id):
                return {"ok": False, "error": "room is full"}
            self._peer_to_room[peer_id] = room_id
            return {"ok": True, "room": room.to_dict()}

    def leave_room(self, peer_id: str) -> dict[str, Any]:
        with self._lock:
            room_id = self._peer_to_room.pop(peer_id, None)
            if not room_id:
                return {"ok": False, "error": "peer not in any room"}
            room = self._rooms.get(room_id)
            if room:
                if room.studio_peer_id == peer_id:
                    room.studio_peer_id = None
                    room.status = "waiting"
                room.remove_viewer(peer_id)
            return {"ok": True, "room_id": room_id}

    def signal_sdp_offer(self, from_peer: str, to_peer: str, sdp: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            room_id = self._peer_to_room.get(from_peer)
            if not room_id:
                return {"ok": False, "error": "peer not in room"}
            room = self._rooms[room_id]
            room.store_sdp_offer(from_peer, sdp)
            return {"ok": True, "room_id": room_id}

    def signal_sdp_answer(self, from_peer: str, to_peer: str, sdp: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            room_id = self._peer_to_room.get(from_peer)
            if not room_id:
                return {"ok": False, "error": "peer not in room"}
            room = self._rooms[room_id]
            room.store_sdp_answer(from_peer, sdp)
            return {"ok": True, "room_id": room_id}

    def relay_ice_candidate(self, from_peer: str, to_peer: str, candidate: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            room_id = self._peer_to_room.get(from_peer)
            if not room_id:
                return {"ok": False, "error": "peer not in room"}
            room = self._rooms[room_id]
            room.add_ice_candidate(from_peer, candidate)
            return {"ok": True, "room_id": room_id}

    def get_pending_signaling(self, peer_id: str) -> dict[str, Any]:
        """Get pending SDP offers/answers and ICE candidates for a peer."""
        with self._lock:
            room_id = self._peer_to_room.get(peer_id)
            if not room_id:
                return {"ok": False, "error": "peer not in room"}
            room = self._rooms[room_id]
            pending_offers = []
            pending_answers = []
            pending_ice = []
            for pid, offer in room.sdp_offers.items():
                if pid != peer_id:
                    pending_offers.append({"from": pid, **offer})
            for pid, answer in room.sdp_answers.items():
                if pid != peer_id:
                    pending_answers.append({"from": pid, **answer})
            for pid, candidates in room.ice_candidates.items():
                if pid != peer_id:
                    pending_ice.extend([{"from": pid, **c} for c in candidates])
            return {
                "ok": True,
                "room_id": room_id,
                "sdp_offers": pending_offers,
                "sdp_answers": pending_answers,
                "ice_candidates": pending_ice,
            }

    def update_stream_stats(self, room_id: str, bitrate_kbps: int = 0, latency_ms: int = 0) -> None:
        with self._lock:
            room = self._rooms.get(room_id)
            if room:
                room.bitrate_kbps = bitrate_kbps
                room.latency_ms = latency_ms

    def close_room(self, room_id: str) -> dict[str, Any]:
        with self._lock:
            room = self._rooms.pop(room_id, None)
            if not room:
                return {"ok": False, "error": "room not found"}
            studio_id = room.studio_id
            if studio_id in self._studios:
                self._studios[studio_id]["active_rooms"] = max(0, self._studios[studio_id]["active_rooms"] - 1)
            for peer_id in list(self._peer_to_room.keys()):
                if self._peer_to_room[peer_id] == room_id:
                    del self._peer_to_room[peer_id]
            return {"ok": True, "room_id": room_id}

    def generate_peer_id(self) -> str:
        return f"peer_{secrets.token_hex(8)}"

    def get_studio_config(self) -> dict[str, Any]:
        """Return recommended WebRTC configuration for studio broadcasters."""
        return {
            "ice_servers": [
                {"urls": "stun:stun.l.google.com:19302"},
                {"urls": "stun:stun1.l.google.com:19302"},
                {"urls": "stun:global.stun.twilio.com:3478"},
            ],
            "codec_preferences": ["VP9", "VP8", "H264"],
            "bitrate": {
                "min": 500,
                "start": 2500,
                "max": 4000,
            },
            "resolution": {
                "width": 1920,
                "height": 1080,
                "frameRate": 60,
            },
            "audio": {
                "echoCancellation": True,
                "noiseSuppression": True,
                "autoGainControl": True,
            },
        }


webrtc_engine = WebRTCStreamEngine()
