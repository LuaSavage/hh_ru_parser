"""Потокобезопасный пул прокси со scoring и ранжированием для proxy race."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from .entry import ProxyEntry, format_addr, host_port

logger = logging.getLogger(__name__)

DEFAULT_RACE_WORKERS = 8


class ProxyPool:
    """Хранилище найденных прокси и их репутации.

    Discovery добавляет прокси через add(); ProxyRace читает ranked() и
    обновляет счётчики через record_success / record_failure.

    Ранжирование: сначала меньше failures, при равенстве — больше successes,
    затем стабильная сортировка по addr. Так в гонку попадают «проверенные»
    прокси, а явно плохие уходят в хвост.
    """

    def __init__(self, on_first_proxy: Callable[[str, float], None] | None = None) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, ProxyEntry] = {}
        # Callback вызывается при добавлении первого прокси (для timeline в Discovery).
        self._on_first_proxy = on_first_proxy

    @property
    def available(self) -> bool:
        with self._lock:
            return len(self._entries) > 0

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def add(self, host: str, port: int, *, search_started_at: float | None = None) -> None:
        """Регистрирует прокси от proxybroker; дубликаты по addr игнорируются."""
        addr = format_addr(host, port)
        with self._lock:
            is_new = addr not in self._entries
            if is_new:
                self._entries[addr] = ProxyEntry(addr=addr)
            count = len(self._entries)

        if not is_new:
            return

        elapsed_s = time.monotonic() - search_started_at if search_started_at else 0.0
        if count == 1 and self._on_first_proxy is not None:
            self._on_first_proxy(addr, elapsed_s)
        logger.debug(
            "Proxy collected addr=%s count_so_far=%s elapsed_s=%.1f",
            host_port(addr),
            count,
            elapsed_s,
        )

    def record_success(self, addr: str) -> None:
        with self._lock:
            entry = self._entries.get(addr)
            if entry is not None:
                entry.successes += 1

    def record_failure(self, addr: str) -> None:
        with self._lock:
            entry = self._entries.get(addr)
            if entry is not None:
                entry.failures += 1

    def _sorted_entries(self, *, reverse_worst: bool = False) -> list[ProxyEntry]:
        """Общая сортировка для ranked / top / bottom — без дублирования ключей."""
        with self._lock:
            entries = list(self._entries.values())
        if reverse_worst:
            return sorted(entries, key=lambda entry: (-entry.failures, entry.successes))
        return sorted(entries, key=lambda entry: (entry.failures, -entry.successes, entry.addr))

    def ranked(self, limit: int = DEFAULT_RACE_WORKERS) -> list[ProxyEntry]:
        """Топ-N прокси для параллельной гонки (по умолчанию 8 воркеров)."""
        return self._sorted_entries()[:limit]

    def addresses(self) -> list[str]:
        return [entry.addr for entry in self._sorted_entries()]

    def export_stats(self) -> list[dict[str, Any]]:
        """Снимок пула для CrawlStats и финального отчёта."""
        return [self._entry_stats(entry) for entry in self._sorted_entries()]

    def top(self, limit: int = 5) -> list[dict[str, Any]]:
        return [self._entry_stats(entry) for entry in self._sorted_entries()[:limit]]

    def bottom(self, limit: int = 5) -> list[dict[str, Any]]:
        return [self._entry_stats(entry) for entry in self._sorted_entries(reverse_worst=True)[:limit]]

    @staticmethod
    def _entry_stats(entry: ProxyEntry) -> dict[str, Any]:
        return {
            "addr": host_port(entry.addr),
            "failures": entry.failures,
            "successes": entry.successes,
        }
