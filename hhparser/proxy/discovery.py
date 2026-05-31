"""Поиск бесплатных HTTP-прокси через proxybroker (blocking или фоновый поток)."""

from __future__ import annotations

import asyncio
import logging
import threading
import time

from proxybroker import Broker

from .entry import host_port
from .pool import ProxyPool

logger = logging.getLogger(__name__)

# proxybroker сверяет exit IP с реальным только для HTTP (не HTTPS/SOCKS).
_BROKER_PROXY_TYPES = [("HTTP", "High Anonymous")]


class ProxyDiscovery:
    """Асинхронный сбор прокси и timeline поиска.

    Broker.find кладёт найденные прокси в asyncio.Queue; _collect_from_queue
    переносит их в ProxyPool. Если за раунд набралось меньше min_proxies —
    поиск повторяется (HH race нужен запас кандидатов).

    В фоновом режиме (start_background) краулинг стартует сразу, прокси
    подтягиваются параллельно — для adaptive use_proxy в VacancyScrapper.
    """

    def __init__(self, pool: ProxyPool) -> None:
        self._pool = pool
        pool._on_first_proxy = self._on_first_proxy
        self._search_started_at: float | None = None
        self._first_found_at: float | None = None
        self._search_finished_at: float | None = None
        self._background_thread: threading.Thread | None = None

    @property
    def search_started_at(self) -> float | None:
        return self._search_started_at

    @property
    def first_found_at(self) -> float | None:
        return self._first_found_at

    @property
    def search_finished_at(self) -> float | None:
        return self._search_finished_at

    def _on_first_proxy(self, addr: str, elapsed_s: float) -> None:
        """Фиксирует момент, когда пул стал непустым — для метрик crawl."""
        self._first_found_at = time.monotonic()
        logger.info(
            "First proxy available elapsed_s=%.1f count=1 addr=%s",
            elapsed_s,
            host_port(addr),
        )

    async def _collect_from_queue(self, proxies: asyncio.Queue) -> None:
        """Читает очередь broker до sentinel None и добавляет прокси в pool."""
        while True:
            proxy = await proxies.get()
            if proxy is None:
                break
            self._pool.add(
                proxy.host,
                proxy.port,
                search_started_at=self._search_started_at,
            )

    async def _run_broker(self, limit: int) -> None:
        """Один раунд Broker.find + сбор результатов в pool."""
        proxies = asyncio.Queue()
        # stop_broker_on_sigint=False — иначе фоновый поток ловит SIGINT краулера.
        broker = Broker(proxies, timeout=3, verify_ssl=True, stop_broker_on_sigint=False)
        await asyncio.gather(
            broker.find(types=_BROKER_PROXY_TYPES, limit=limit),
            self._collect_from_queue(proxies),
        )

    def _search_loop(self, limit: int, min_proxies: int, *, blocking_label: str) -> None:
        """Повторяет раунды поиска, пока не наберётся min_proxies или broker исчерпан."""
        while True:
            round_started = time.monotonic()
            asyncio.run(self._run_broker(limit))
            found = self._pool.count()
            logger.info(
                "Proxy search round finished found=%s duration_s=%.1f",
                found,
                time.monotonic() - round_started,
            )
            if found >= min_proxies:
                break
            logger.warning(
                "Fewer than %s proxies found (%s), retrying search",
                min_proxies,
                found,
            )

        self._search_finished_at = time.monotonic()
        logger.info(
            "%s proxy search finished total_found=%s total_duration_s=%.1f",
            blocking_label,
            self._pool.count(),
            self._search_finished_at - (self._search_started_at or self._search_finished_at),
        )

    def find_blocking(self, limit: int, min_proxies: int) -> None:
        """Блокирует вызывающий поток до завершения поиска (режим use_proxy=always)."""
        self._search_started_at = time.monotonic()
        logger.info("Blocking proxy search started limit=%s", limit)
        self._search_loop(limit, min_proxies, blocking_label="Blocking")

    def start_background(self, limit: int, min_proxies: int) -> None:
        """Запускает daemon-поток поиска; повторный вызов игнорируется, если поток жив."""
        if self._background_thread and self._background_thread.is_alive():
            return

        self._search_started_at = time.monotonic()
        logger.info(
            "Background proxy search started limit=%s thread=%s",
            limit,
            threading.current_thread().name,
        )
        self._background_thread = threading.Thread(
            target=self._run_background,
            args=(limit, min_proxies),
            name="proxybroker-search",
            daemon=True,
        )
        self._background_thread.start()

    def _run_background(self, limit: int, min_proxies: int) -> None:
        self._search_loop(limit, min_proxies, blocking_label="Background")
