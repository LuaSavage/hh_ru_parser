"""Оркестрация краулинга HH: поиск, ссылки на vacancy, выбор direct vs proxy."""

import logging
import random
import time
from typing import Literal

import requests
from fake_headers import Headers

from .crawl_stats import CrawlStats
from .page_fetcher import PageFetcher
from .proxy import (
    DEFAULT_PROXY_CONNECT_TIMEOUT,
    DEFAULT_PROXY_READ_TIMEOUT,
    DEFAULT_RACE_WORKERS,
    Proxy,
)
from .proxy_race import FetchLogger, ProxyRace

logger = logging.getLogger(__name__)

UseProxyMode = Literal["always", "never", "adaptive"]
DIRECT_TIMEOUT = 30


class VacancyScrapper:
    """Публичный API краулера вакансий hh.ru.

    Тяжёлая работа делегирована:
    - PageFetcher — HTTP + валидация HTML;
    - Proxy / ProxyRace — fallback через прокси;
    - FetchLogger + CrawlStats — телеметрия.

    Режимы use_proxy:
    - never — только прямой IP;
    - always — vacancy только через proxy race (поиск прокси блокирует старт);
    - adaptive — поиск в фоне, vacancy: 2 direct попытки, затем race если пул не пуст.
    """

    __url_search = "https://hh.ru/search/vacancy"
    __url_vacancy = "https://hh.ru/vacancy"

    @classmethod
    def get_search_url(cls):
        return cls.__url_search

    @classmethod
    def get_vacancy_url(cls):
        return cls.__url_vacancy

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:91.0) Firefox/91.0",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Connection": "keep-alive",
    }

    __fake_header = Headers()

    params = {"salary": None, "st": "searchVacancy", "text": "", "page": 0}

    sleep_time = {"min": 0.1, "max": 1}

    def __init__(
        self,
        params=None,
        sleep_time=None,
        use_proxy: bool | UseProxyMode = "adaptive",
        proxy_timeout: int = DEFAULT_PROXY_READ_TIMEOUT,
        proxy_race_workers: int = DEFAULT_RACE_WORKERS,
    ):
        if sleep_time:
            self.sleep_time = sleep_time
        if params:
            self.params = params

        self._use_proxy_mode = self._normalize_use_proxy(use_proxy)
        self._proxy_timeout = (DEFAULT_PROXY_CONNECT_TIMEOUT, proxy_timeout)
        self._proxy_race_workers = proxy_race_workers
        self._crawl_started_at = time.monotonic()
        self.stats = CrawlStats(
            proxy_mode=self._use_proxy_mode,
            crawl_started_at=self._crawl_started_at,
        )
        self._direct_session = requests.Session()
        self._fetcher = PageFetcher(self._direct_session)
        self._fetch_logger = FetchLogger(self.stats)
        self.proxy: Proxy | None = None
        self._proxy_race: ProxyRace | None = None

        if self._use_proxy_mode == "never":
            logger.info("VacancyScrapper initialized use_proxy=never (direct only)")
        elif self._use_proxy_mode == "always":
            logger.info("VacancyScrapper initialized use_proxy=always (blocking proxy search)")
            self.proxy = Proxy(background=False)
            self._init_proxy_race()
            self._sync_proxy_stats()
        else:
            logger.info("VacancyScrapper initialized use_proxy=adaptive (background proxy search)")
            self.proxy = Proxy(background=True)
            self._init_proxy_race()
            self.stats.proxy_search_started_at = self.proxy.search_started_at

    def _init_proxy_race(self) -> None:
        """Собирает ProxyRace после того, как proxy и pool уже созданы."""
        if self.proxy is None:
            return
        self._proxy_race = ProxyRace(
            self.proxy.pool,
            self._fetcher,
            self._fetch_logger,
            self.stats,
            workers=self._proxy_race_workers,
            timeout=self._proxy_timeout,
            headers_factory=self._build_headers,
        )

    @staticmethod
    def _normalize_use_proxy(use_proxy: bool | UseProxyMode) -> UseProxyMode:
        if use_proxy is True:
            return "always"
        if use_proxy is False:
            return "never"
        return use_proxy

    def _build_headers(self) -> dict[str, str]:
        return self.__fake_header.generate() or self.headers

    def _sync_proxy_stats(self) -> None:
        """Копирует timeline broker и снимок пула в CrawlStats (режим always)."""
        if self.proxy is None:
            return
        self.stats.sync_proxy_timeline(
            search_started_at=self.proxy.search_started_at,
            first_found_at=self.proxy.first_found_at,
            search_finished_at=self.proxy.search_finished_at,
            proxies_count=self.proxy.count(),
            proxy_pool_snapshot=self.proxy.export_stats(),
        )

    def __wait(self) -> None:
        time.sleep(
            self.sleep_time["min"]
            + (random.random() * (self.sleep_time["max"] - self.sleep_time["min"]))
        )

    def _fetch_page(
        self,
        url: str,
        *,
        use_params: bool = True,
        max_attempts: int = 2,
        kind: str = "search",
        vacancy_id: int | None = None,
        page_label: str | None = None,
    ):
        """До max_attempts прямых GET с паузой и случайными заголовками."""
        params = self.params if use_params else None

        for attempt in range(1, max_attempts + 1):
            self.__wait()
            headers = self._build_headers()
            logger.debug(
                "GET %s params=%s via_proxy=false attempt=%s/%s",
                url,
                params,
                attempt,
                max_attempts,
            )
            result = self._fetcher.fetch_direct(
                url,
                headers=headers,
                params=params,
                kind=kind,
                timeout=DIRECT_TIMEOUT,
            )
            success = result.page is not None
            self._fetch_logger.record(
                url=url,
                kind=kind,
                via_proxy=False,
                attempt=attempt,
                max_attempts=max_attempts,
                status_code=result.status_code,
                duration_s=result.duration_s,
                success=success,
                error=result.error,
                vacancy_id=vacancy_id,
                proxy_addr=None,
                page_label=page_label,
                race_id=None,
            )
            if success:
                return result.page

        return None

    def _run_proxy_race(self, url: str, *, vacancy_id: int | None):
        if self._proxy_race is None:
            return None
        return self._proxy_race.run(
            url,
            params=None,
            kind="vacancy",
            vacancy_id=vacancy_id,
        )

    def get_page(self, url, use_params=True):
        return self._fetch_page(
            url,
            use_params=use_params,
            max_attempts=2,
            kind="search" if use_params else "vacancy",
        )

    def get_vacancy_page(self, url=None, id=None):
        """Загрузка страницы вакансии с учётом use_proxy mode.

        always: сразу proxy race.
        never / adaptive: сначала direct (2 попытки); adaptive при провале — race,
        если к моменту fallback пул уже наполнился.
        """
        vacancy_id: int | None = None
        if id:
            url = self.__url_vacancy + "/" + id
            vacancy_id = int(id)

        if self._use_proxy_mode == "always":
            page = self._run_proxy_race(url, vacancy_id=vacancy_id)
            if page is not None:
                self.stats.record_vacancy_proxy_ok()
            else:
                self.stats.record_vacancy_proxy_failed()
            return page

        page = self._fetch_page(
            url,
            use_params=False,
            max_attempts=2,
            kind="vacancy",
            vacancy_id=vacancy_id,
        )
        if page is not None:
            self.stats.record_vacancy_direct_ok()
            return page

        if self._use_proxy_mode == "adaptive" and self.proxy is not None and self.proxy.available:
            logger.info(
                "Vacancy fallback to proxy race vacancy_id=%s proxies_available=%s",
                vacancy_id,
                self.proxy.count(),
            )
            page = self._run_proxy_race(url, vacancy_id=vacancy_id)
            if page is not None:
                self.stats.record_vacancy_proxy_ok()
                return page
            self.stats.record_vacancy_proxy_failed()
            return None

        self.stats.record_vacancy_direct_failed()
        return None

    def get_searching_results_page(self, page_number=None, page_count: int | None = None):
        page_number = page_number or 0
        self.params["page"] = page_number
        page_label = None
        if page_count is not None:
            page_label = f"{page_number + 1}/{page_count}"
        return self._fetch_page(
            self.__url_search,
            use_params=True,
            max_attempts=2,
            kind="search",
            page_label=page_label,
        )

    def get_page_count(self):
        from .template_parser import DumpParser

        response = self.get_searching_results_page()
        return DumpParser.get_search_page_count(response)

    def get_vacancy_links(self):
        """Обходит все страницы поиска и собирает URL вакансий.

        При пустом parse_search_page повторяет запрос той же страницы —
        HH иногда отдаёт заглушку без списка.
        """
        from .template_parser import DumpParser

        links = []

        page_count = self.get_page_count()
        for page_number in range(page_count):
            vacancies = []
            while not vacancies:
                response = self.get_searching_results_page(
                    page_number=page_number,
                    page_count=page_count,
                )
                vacancies = DumpParser.parse_search_page(response)

            for vacancy in vacancies:
                links.append(vacancy["url"])

        return links
