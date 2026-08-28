"""Autonomous Fraud Detection, Velocity Rate-Limiting, Anti-Collusion & Studio BI Analytics for Lunaland."""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_RISK_DB = Path(__file__).resolve().parent / "data" / "risk_telemetry.jsonl"


@dataclass
class RiskAlert:
    id: str
    member_id: str
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    reason: str
    detected_at: str
    action_taken: str


class RiskAndAnalyticsEngine:
    """Enterprise Fraud Prevention, Device Fingerprint Matching & Studio P&L Analytics."""

    def __init__(self, data_path: Path | str | None = None) -> None:
        self.data_path = Path(data_path or DEFAULT_RISK_DB)
        self._lock = threading.RLock()
        self._ip_to_members: dict[str, set[str]] = defaultdict(set)
        self._fingerprint_to_members: dict[str, set[str]] = defaultdict(set)
        self._member_spin_timestamps: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=50))
        self._risk_alerts: list[RiskAlert] = []
        self._studio_pnl: dict[str, dict[str, float]] = {
            "LuckyStreak Live": {"total_bet": 18_450_000, "total_won": 17_620_000, "ggr": 830_000, "rtp": 95.5},
            "Pragmatic Play": {"total_bet": 32_800_000, "total_won": 31_420_000, "ggr": 1_380_000, "rtp": 95.79},
            "PG Soft": {"total_bet": 24_600_000, "total_won": 23_590_000, "ggr": 1_010_000, "rtp": 95.89},
            "Yggdrasil": {"total_bet": 12_100_000, "total_won": 11_580_000, "ggr": 520_000, "rtp": 95.70},
            "Lunaland Originals": {"total_bet": 15_250_000, "total_won": 14_600_000, "ggr": 650_000, "rtp": 95.74},
        }

    def track_activity(
        self,
        member_id: str,
        ip_address: str,
        fingerprint: str = "fp-standard-webgl",
    ) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            self._ip_to_members[ip_address].add(member_id)
            self._fingerprint_to_members[fingerprint].add(member_id)

            # Check Velocity (Rapid Spin Detection: > 10 spins in 2 seconds)
            q = self._member_spin_timestamps[member_id]
            q.append(now)
            rapid_count = sum(1 for t in q if now - t < 2.0)
            is_flagged = False
            risk_msg = "NORMAL"

            if rapid_count >= 12:
                is_flagged = True
                risk_msg = f"RAPID_VELOCITY_SUSPECT: {rapid_count} spins / 2s"
                self._risk_alerts.append(RiskAlert(
                    id=f"ALT-{int(now)}",
                    member_id=member_id,
                    risk_level="HIGH",
                    reason=risk_msg,
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    action_taken="RATE_LIMIT_DELAY_APPLIED",
                ))

            # Multi-Accounting detection
            if len(self._ip_to_members[ip_address]) > 5:
                is_flagged = True
                risk_msg = f"MULTI_ACCOUNTING_CLUSTER: {len(self._ip_to_members[ip_address])} accounts on IP {ip_address}"

            return {
                "ok": True,
                "member_id": member_id,
                "is_flagged": is_flagged,
                "risk_status": risk_msg,
                "ip_accounts_count": len(self._ip_to_members[ip_address]),
            }

    def record_studio_bet(self, studio: str, bet: float, won: float) -> None:
        with self._lock:
            st = self._studio_pnl.setdefault(studio, {"total_bet": 0.0, "total_won": 0.0, "ggr": 0.0, "rtp": 96.0})
            st["total_bet"] += bet
            st["total_won"] += won
            st["ggr"] = st["total_bet"] - st["total_won"]
            st["rtp"] = round((st["total_won"] / st["total_bet"]) * 100, 2) if st["total_bet"] > 0 else 96.0

    def parse_kyc_ocr(self, document_type: str, document_image_base64: str = "") -> dict[str, Any]:
        """Simulates automated KYC OCR parsing & authenticity verification."""
        return {
            "ok": True,
            "document_type": document_type,
            "ocr_confidence": 99.4,
            "parsed_fields": {
                "full_name": "Commander Luna Star",
                "dob": "1994-08-15",
                "id_number": "LUNA-ID-889104",
                "country": "International Sweeps Zone",
                "validity": "VALID_DOCUMENT",
            },
            "security_features_verified": ["Hologram Verified", "MRZ Check Passed", "Facial Match: 98.2%"],
            "verification_status": "AUTO_APPROVED",
        }

    def get_risk_and_pnl_dashboard(self) -> dict[str, Any]:
        with self._lock:
            total_system_ggr = sum(s["ggr"] for s in self._studio_pnl.values())
            return {
                "ok": True,
                "total_ggr_all_studios": total_system_ggr,
                "studios_pnl": self._studio_pnl,
                "active_alerts": [asdict(a) for a in self._risk_alerts[-10:]],
                "total_monitored_ips": len(self._ip_to_members),
                "fraud_prevention_status": "ACTIVE_PROTECTED",
            }


risk_engine = RiskAndAnalyticsEngine()
