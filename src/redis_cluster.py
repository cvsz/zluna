"""Distributed Redis Cluster Support for ZLUNA Multi-Node Horizontal Scaling.

Provides Redis-backed event pub/sub, shared state storage, and distributed
session management for running multiple zluna server instances behind a load balancer.

Falls back to in-memory implementations when Redis is unavailable.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any


class InMemoryEventBus:
    """Fallback in-memory event bus when Redis is unavailable."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[Any]] = {}

    def publish(self, channel: str, message: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers.get(channel, []))
        for sub in subs:
            try:
                sub.put_nowait(message)
            except Exception:
                pass

    def subscribe(self, channel: str, queue: Any) -> None:
        with self._lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = []
            self._subscribers[channel].append(queue)

    def unsubscribe(self, channel: str, queue: Any) -> None:
        with self._lock:
            if channel in self._subscribers:
                try:
                    self._subscribers[channel].remove(queue)
                except ValueError:
                    pass


class RedisClusterManager:
    """Manages Redis cluster connections for distributed zluna deployments."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._redis_client = None
        self._pubsub = None
        self._node_id = f"node_{secrets.token_hex(6)}"
        self._cluster_enabled = False
        self._fallback_bus = InMemoryEventBus()
        self._prefix = "zluna"
        self._startup_time = datetime.now(timezone.utc).isoformat()

    def configure(self, urls: list[str] | None = None, password: str | None = None) -> dict[str, Any]:
        """Configure Redis cluster connection. Returns status."""
        with self._lock:
            if urls is None:
                env_url = os.environ.get("REDIS_CLUSTER_URL", os.environ.get("REDIS_URL", ""))
                if env_url:
                    urls = [env_url]
                else:
                    urls = []
            if not urls:
                self._cluster_enabled = False
                return {"ok": True, "cluster": False, "node_id": self._node_id, "reason": "no_redis_configured"}
            try:
                import redis
                from redis.cluster import RedisCluster
                startup_nodes = []
                for url in urls:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    startup_nodes.append({"host": parsed.hostname or "127.0.0.1", "port": parsed.port or 6379})
                if len(startup_nodes) > 1:
                    self._redis_client = RedisCluster(startup_nodes=startup_nodes, password=password, decode_responses=True, skip_full_coverage_check=True)
                else:
                    self._redis_client = redis.Redis(host=startup_nodes[0]["host"], port=startup_nodes[0]["port"], password=password, decode_responses=True)
                self._redis_client.ping()
                self._cluster_enabled = True
                self._prefix = os.environ.get("REDIS_PREFIX", "zluna")
                return {"ok": True, "cluster": True, "node_id": self._node_id, "urls": urls}
            except ImportError:
                self._cluster_enabled = False
                return {"ok": True, "cluster": False, "node_id": self._node_id, "reason": "redis_py_not_installed"}
            except Exception as exc:
                self._cluster_enabled = False
                return {"ok": True, "cluster": False, "node_id": self._node_id, "reason": str(exc)}

    @property
    def is_cluster_enabled(self) -> bool:
        return self._cluster_enabled

    @property
    def node_id(self) -> str:
        return self._node_id

    def _key(self, *parts: str) -> str:
        return f"{self._prefix}:" + ":".join(parts)

    def register_node(self, host: str, port: int) -> dict[str, Any]:
        """Register this node in the cluster registry."""
        node_info = {
            "node_id": self._node_id,
            "host": host,
            "port": port,
            "started_at": self._startup_time,
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }
        if self._cluster_enabled and self._redis_client:
            try:
                self._redis_client.hset(self._key("nodes"), self._node_id, json.dumps(node_info))
                self._redis_client.expire(self._key("nodes"), 300)
            except Exception:
                pass
        return {"ok": True, "node": node_info}

    def heartbeat(self) -> None:
        """Send heartbeat to cluster."""
        if self._cluster_enabled and self._redis_client:
            try:
                data = self._redis_client.hget(self._key("nodes"), self._node_id)
                if data:
                    node_info = json.loads(data)
                    node_info["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
                    self._redis_client.hset(self._key("nodes"), self._node_id, json.dumps(node_info))
                    self._redis_client.expire(self._key("nodes"), 300)
            except Exception:
                pass

    def list_nodes(self) -> list[dict[str, Any]]:
        """List all active nodes in the cluster."""
        if self._cluster_enabled and self._redis_client:
            try:
                nodes = self._redis_client.hgetall(self._key("nodes"))
                result = []
                for nid, data in nodes.items():
                    try:
                        result.append(json.loads(data))
                    except json.JSONDecodeError:
                        continue
                return result
            except Exception:
                return []
        return [{"node_id": self._node_id, "status": "standalone", "started_at": self._startup_time}]

    def publish_event(self, channel: str, message: dict[str, Any]) -> None:
        """Publish event to Redis pub/sub or fallback bus."""
        enriched = {**message, "node_id": self._node_id, "published_at": datetime.now(timezone.utc).isoformat()}
        if self._cluster_enabled and self._redis_client:
            try:
                self._redis_client.publish(self._key("events", channel), json.dumps(enriched))
                return
            except Exception:
                pass
        self._fallback_bus.publish(channel, enriched)

    def store_shared_state(self, key: str, value: dict[str, Any], ttl: int = 3600) -> bool:
        """Store shared state accessible by all nodes."""
        if self._cluster_enabled and self._redis_client:
            try:
                self._redis_client.setex(self._key("state", key), ttl, json.dumps(value))
                return True
            except Exception:
                return False
        return False

    def get_shared_state(self, key: str) -> dict[str, Any] | None:
        """Retrieve shared state from any node."""
        if self._cluster_enabled and self._redis_client:
            try:
                data = self._redis_client.get(self._key("state", key))
                if data:
                    return json.loads(data)
            except Exception:
                return None
        return None

    def acquire_lock(self, lock_name: str, ttl: int = 30) -> str | None:
        """Acquire a distributed lock. Returns lock token or None."""
        token = secrets.token_hex(16)
        if self._cluster_enabled and self._redis_client:
            try:
                acquired = self._redis_client.set(self._key("lock", lock_name), token, nx=True, ex=ttl)
                if acquired:
                    return token
                return None
            except Exception:
                return None
        return token

    def release_lock(self, lock_name: str, token: str) -> bool:
        """Release a distributed lock."""
        if self._cluster_enabled and self._redis_client:
            try:
                lock_key = self._key("lock", lock_name)
                current = self._redis_client.get(lock_key)
                if current == token:
                    self._redis_client.delete(lock_key)
                    return True
                return False
            except Exception:
                return False
        return True

    def increment_counter(self, counter_name: str, amount: int = 1) -> int:
        """Atomic counter increment across cluster."""
        if self._cluster_enabled and self._redis_client:
            try:
                return self._redis_client.incrby(self._key("counter", counter_name), amount)
            except Exception:
                return 0
        return 0

    def get_cluster_status(self) -> dict[str, Any]:
        """Get overall cluster health status."""
        nodes = self.list_nodes()
        return {
            "ok": True,
            "cluster_enabled": self._cluster_enabled,
            "node_id": self._node_id,
            "total_nodes": len(nodes),
            "nodes": nodes,
            "mode": "cluster" if self._cluster_enabled else "standalone",
        }


redis_cluster = RedisClusterManager()
