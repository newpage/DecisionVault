from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any


@dataclass
class CacheEntry:
    expires_at: float
    value: dict[str, Any]


class DashboardCache:
    def __init__(self, ttl_seconds: int = 30):
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, tenant_id: str) -> dict[str, Any] | None:
        now = monotonic()
        with self._lock:
            entry = self._entries.get(tenant_id)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._entries.pop(tenant_id, None)
                return None
            return entry.value

    def set(self, tenant_id: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._entries[tenant_id] = CacheEntry(
                expires_at=monotonic() + self.ttl_seconds,
                value=value,
            )

    def invalidate(self, tenant_id: str) -> None:
        with self._lock:
            self._entries.pop(tenant_id, None)


dashboard_cache = DashboardCache(ttl_seconds=30)
