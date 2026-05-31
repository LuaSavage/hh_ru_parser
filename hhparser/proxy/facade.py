"""Публичный фасад Proxy — совместим с прежним import path ``from hhparser.proxy import Proxy``."""

from __future__ import annotations

from typing import Any

from .discovery import ProxyDiscovery
from .entry import ProxyEntry
from .pool import DEFAULT_RACE_WORKERS, ProxyPool

DEFAULT_PROXY_READ_TIMEOUT = 5
DEFAULT_PROXY_CONNECT_TIMEOUT = 3


class Proxy:
    """Тонкая обёртка над ProxyPool + ProxyDiscovery.

    Снаружи остаётся прежний API: available, count, timeline, ranked_for_race,
    export_stats. Внутри pool отдаётся ProxyRace напрямую (без лишних делегатов).

    background=True — поиск в фоне (adaptive); False — блокирующий старт (always).
    """

    def __init__(self, *, background: bool = False, limit: int = 50, min_proxies: int = 2):
        self._pool = ProxyPool()
        self._discovery = ProxyDiscovery(self._pool)
        self._limit = limit
        self._min_proxies = min_proxies

        if background:
            self._discovery.start_background(limit, min_proxies)
        else:
            self._discovery.find_blocking(limit, min_proxies)

    @property
    def pool(self) -> ProxyPool:
        """Прямой доступ к пулу для ProxyRace (scoring без обхода через фасад)."""
        return self._pool

    @property
    def list(self) -> list[str]:
        return self._pool.addresses()

    @property
    def available(self) -> bool:
        return self._pool.available

    @property
    def search_started_at(self) -> float | None:
        return self._discovery.search_started_at

    @property
    def first_found_at(self) -> float | None:
        return self._discovery.first_found_at

    @property
    def search_finished_at(self) -> float | None:
        return self._discovery.search_finished_at

    def count(self) -> int:
        return self._pool.count()

    def record_success(self, addr: str) -> None:
        self._pool.record_success(addr)

    def record_failure(self, addr: str) -> None:
        self._pool.record_failure(addr)

    def ranked_for_race(self, limit: int = DEFAULT_RACE_WORKERS) -> list[ProxyEntry]:
        return self._pool.ranked(limit)

    def export_stats(self) -> list[dict[str, Any]]:
        return self._pool.export_stats()

    def pool_top(self, limit: int = 5) -> list[dict[str, Any]]:
        return self._pool.top(limit)

    def pool_bottom(self, limit: int = 5) -> list[dict[str, Any]]:
        return self._pool.bottom(limit)
