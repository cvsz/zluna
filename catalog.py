"""Local game catalog metadata for zslog synthetic games with Lunaland Providers."""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from games import list_games


@dataclass
class GameMetadata:
    game_id: str
    name: str
    description: str
    category: str
    provider: str = "Lunaland Original"
    tags: list[str] = field(default_factory=list)
    min_bet: int = 1
    max_bet: int = 1000
    rtp: float | None = 96.5
    volatility: str | None = "Medium"
    thumbnail: str | None = None
    images: list[str] = field(default_factory=list)
    featured: bool = False
    status: str = "available"
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "provider": self.provider,
            "tags": self.tags,
            "min_bet": self.min_bet,
            "max_bet": self.max_bet,
            "rtp": self.rtp,
            "volatility": self.volatility,
            "thumbnail": self.thumbnail,
            "images": self.images,
            "featured": self.featured,
            "status": self.status,
            "updated_at": self.updated_at,
            "extra": self.extra,
        }


@dataclass
class CatalogEntry:
    metadata: GameMetadata
    favorite: bool = False
    last_played_at: str | None = None
    play_count: int = 0
    source: str = "lunaland-seed"
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = self.metadata.to_dict()
        data.update({
            "favorite": self.favorite,
            "last_played_at": self.last_played_at,
            "play_count": self.play_count,
            "source": self.source,
            "provenance": self.provenance,
        })
        return data


def _seed_catalog() -> list[CatalogEntry]:
    entries = []
    for game in list_games():
        category = game.get("category", "other") or "other"
        tags = [category]
        if category == "slots":
            tags += ["slots", "megaways", "popular"]
        elif category == "table":
            tags += ["table", "cards", "skill"]
        elif category == "instant":
            tags += ["fast", "instant", "arcade"]
        elif category == "lottery":
            tags += ["numbers", "draw"]
            
        provider = game.get("provider", "Lunaland Original")
        tags.append(provider.lower().replace(" ", "-"))

        provenance = {
            "source": "lunaland-seed",
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "external_id": game["id"],
        }
        entry = CatalogEntry(
            metadata=GameMetadata(
                game_id=game["id"],
                name=game["name"],
                description=game["description"],
                category=category,
                provider=provider,
                tags=tags,
                min_bet=game.get("min_bet", 1),
                max_bet=game.get("max_bet", 1000),
                rtp=game.get("rtp", 96.5),
                volatility=game.get("volatility", "Medium"),
                featured=game.get("featured", False),
                status="available",
                updated_at=datetime.now(timezone.utc).isoformat(),
            ),
            favorite=False,
            last_played_at=None,
            play_count=0,
            source="lunaland-seed",
            provenance=provenance,
        )
        entries.append(entry)
    return entries


class GameCatalog:
    def __init__(self) -> None:
        self._entries: dict[str, CatalogEntry] = {}
        self._lock = threading.RLock()
        self._load_seed()

    def _load_seed(self) -> None:
        for entry in _seed_catalog():
            self._entries[entry.metadata.game_id] = entry

    def list_games(
        self,
        *,
        query: str = "",
        category: str = "",
        provider: str = "",
        tags: list[str] | None = None,
        favorites_only: bool = False,
        status: str = "",
        page: int = 1,
        page_size: int = 20,
        sort: str = "name",
    ) -> tuple[list[dict], int]:
        with self._lock:
            items = list(self._entries.values())
        if query:
            q = query.lower()
            items = [
                item
                for item in items
                if q in item.metadata.name.lower()
                or q in item.metadata.description.lower()
                or any(q in tag.lower() for tag in item.metadata.tags)
            ]
        if category:
            items = [item for item in items if item.metadata.category == category]
        if provider:
            items = [item for item in items if item.metadata.provider == provider]
        if tags:
            tag_set = {tag.lower() for tag in tags}
            items = [item for item in items if tag_set.intersection({tag.lower() for tag in item.metadata.tags})]
        if favorites_only:
            items = [item for item in items if item.favorite]
        if status:
            items = [item for item in items if item.metadata.status == status]
        total = len(items)
        if sort == "name":
            items.sort(key=lambda item: item.metadata.name.lower())
        elif sort == "recent":
            items.sort(key=lambda item: item.last_played_at or "", reverse=True)
        elif sort == "popular":
            items.sort(key=lambda item: item.play_count, reverse=True)
        elif sort == "rtp":
            items.sort(key=lambda item: item.metadata.rtp or 0, reverse=True)
        start = max(0, (page - 1) * page_size)
        end = start + page_size
        page_items = items[start:end]
        return [item.to_dict() for item in page_items], total

    def get(self, game_id: str) -> dict | None:
        with self._lock:
            entry = self._entries.get(game_id)
            return entry.to_dict() if entry else None

    def record_play(self, game_id: str) -> None:
        with self._lock:
            entry = self._entries.get(game_id)
            if not entry:
                return
            entry.play_count += 1
            entry.last_played_at = datetime.now(timezone.utc).isoformat()

    def set_favorite(self, game_id: str, favorite: bool) -> None:
        with self._lock:
            entry = self._entries.get(game_id)
            if entry:
                entry.favorite = favorite

    def categories(self) -> list[str]:
        with self._lock:
            return sorted({entry.metadata.category for entry in self._entries.values()})

    def providers(self) -> list[str]:
        with self._lock:
            return sorted({entry.metadata.provider for entry in self._entries.values()})

    def tags(self) -> list[str]:
        with self._lock:
            tag_set = set()
            for entry in self._entries.values():
                tag_set.update(entry.metadata.tags)
            return sorted(tag_set)


catalog = GameCatalog()
