"""Параллельная «гонка» прокси за одну vacancy-страницу и логирование попыток fetch."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup

from .crawl_stats import CrawlStats, RequestRecord
from .page_fetcher import PageFetcher
from .proxy.entry import host_port
from .proxy.pool import ProxyPool

logger = logging.getLogger(__name__)


class FetchLogger:
    """Пишет RequestRecord в CrawlStats и дублирует краткую строку в application log."""

    def __init__(self, stats: CrawlStats) -> None:
        self._stats = stats

    def record(
        self,
        *,
        url: str,
        kind: str,
        via_proxy: bool,
        attempt: int,
        max_attempts: int,
        status_code: int | None,
        duration_s: float,
        success: bool,
        error: str | None,
        vacancy_id: int | None,
        proxy_addr: str | None,
        page_label: str | None,
        race_id: str | None,
    ) -> None:
        record = RequestRecord(
            ts=time.monotonic(),
            url=url,
            kind=kind,
            via_proxy=via_proxy,
            attempt=attempt,
            max_attempts=max_attempts,
            status_code=status_code,
            duration_s=round(duration_s, 3),
            success=success,
            error=error,
            vacancy_id=vacancy_id,
            proxy_addr=proxy_addr,
            page_label=page_label,
            race_id=race_id,
        )
        self._stats.record_request(record)

        log_args = (kind, via_proxy, attempt, max_attempts, status_code, duration_s)
        extra = ""
        if vacancy_id is not None:
            extra += f" vacancy_id={vacancy_id}"
        if page_label:
            extra += f" page={page_label}"
        if proxy_addr:
            extra += f" proxy={proxy_addr}"
        if race_id:
            extra += f" race_id={race_id[:8]}"

        if success:
            logger.info(
                "fetch ok kind=%s via_proxy=%s attempt=%s/%s status=%s duration=%.1fs%s",
                *log_args,
                extra,
            )
        else:
            logger.warning(
                "fetch fail kind=%s via_proxy=%s attempt=%s/%s status=%s duration=%.1fs error=%s%s",
                *log_args,
                error,
                extra,
            )


class ProxyRace:
    """Несколько прокси одновременно запрашивают один URL; побеждает первый валидный ответ.

    Алгоритм:
    1. Берём top-N из ProxyPool.ranked (обычно 8).
    2. ThreadPoolExecutor — по одному fetch_via_proxy на кандидата.
    3. as_completed: как только пришла страница с JSON — break, cancel остальные futures.
    4. Penalty: winner +success, все остальные участники раунда +failure
       (даже если их запрос ещё не завершился — они проиграли гонку).

    headers_factory вызывается один раз на race — один набор заголовков для всех воркеров.
    """

    def __init__(
        self,
        pool: ProxyPool,
        fetcher: PageFetcher,
        fetch_logger: FetchLogger,
        stats: CrawlStats,
        *,
        workers: int = 8,
        timeout: tuple[float, float] = (3, 5),
        headers_factory: Callable[[], dict[str, str]],
    ) -> None:
        self._pool = pool
        self._fetcher = fetcher
        self._fetch_logger = fetch_logger
        self._stats = stats
        self._workers = workers
        self._timeout = timeout
        self._headers_factory = headers_factory

    def run(
        self,
        url: str,
        *,
        params: dict | None,
        kind: str = "vacancy",
        vacancy_id: int | None = None,
    ) -> BeautifulSoup | None:
        if not self._pool.available:
            return None

        candidates = self._pool.ranked(self._workers)
        if not candidates:
            return None

        race_id = str(uuid.uuid4())
        self._stats.record_proxy_race()
        candidate_addrs = [entry.addr for entry in candidates]
        logger.info(
            "Proxy race start vacancy_id=%s candidates=%s race_id=%s",
            vacancy_id,
            len(candidate_addrs),
            race_id[:8],
        )

        headers = self._headers_factory()
        max_attempts = len(candidates)
        winner_page: BeautifulSoup | None = None
        winner_addr: str | None = None
        winner_duration = 0.0

        def run_worker(
            worker_index: int, proxy_addr: str
        ) -> tuple[int, str, BeautifulSoup | None, float, int | None, str | None]:
            result = self._fetcher.fetch_via_proxy(
                url,
                proxy_addr=proxy_addr,
                headers=headers,
                params=params,
                kind=kind,
                timeout=self._timeout,
            )
            return (
                worker_index,
                proxy_addr,
                result.page,
                result.duration_s,
                result.status_code,
                result.error,
            )

        executor = ThreadPoolExecutor(max_workers=len(candidates))
        futures: dict[Future, str] = {
            executor.submit(run_worker, index, entry.addr): entry.addr
            for index, entry in enumerate(candidates, start=1)
        }

        try:
            for future in as_completed(futures):
                worker_index, addr, page, duration_s, status_code, error = future.result()
                success = page is not None

                self._fetch_logger.record(
                    url=url,
                    kind=kind,
                    via_proxy=True,
                    attempt=worker_index,
                    max_attempts=max_attempts,
                    status_code=status_code,
                    duration_s=duration_s,
                    success=success,
                    error=error,
                    vacancy_id=vacancy_id,
                    proxy_addr=host_port(addr),
                    page_label=None,
                    race_id=race_id,
                )

                if success and winner_page is None:
                    winner_page = page
                    winner_addr = addr
                    winner_duration = duration_s
                    break
        finally:
            # Не ждём timeout проигравших — отменяем висящие запросы.
            executor.shutdown(wait=False, cancel_futures=True)

        if winner_page is not None and winner_addr is not None:
            self._pool.record_success(winner_addr)
            for addr in candidate_addrs:
                if addr != winner_addr:
                    self._pool.record_failure(addr)
            logger.info(
                "Proxy race win vacancy_id=%s proxy=%s duration=%.1fs losers=%s race_id=%s",
                vacancy_id,
                host_port(winner_addr),
                winner_duration,
                len(candidate_addrs) - 1,
                race_id[:8],
            )
            return winner_page

        for addr in candidate_addrs:
            self._pool.record_failure(addr)
        logger.warning(
            "Proxy race all failed vacancy_id=%s candidates=%s race_id=%s",
            vacancy_id,
            len(candidate_addrs),
            race_id[:8],
        )
        return None
