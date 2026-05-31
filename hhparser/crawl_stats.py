from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RequestRecord:
    ts: float
    url: str
    kind: str
    via_proxy: bool
    attempt: int
    max_attempts: int
    status_code: int | None
    duration_s: float
    success: bool
    error: str | None = None
    vacancy_id: int | None = None
    proxy_addr: str | None = None
    page_label: str | None = None
    race_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CrawlStats:
    proxy_mode: str
    crawl_started_at: float
    proxy_search_started_at: float | None = None
    proxy_first_found_at: float | None = None
    proxy_search_finished_at: float | None = None
    proxies_found_total: int = 0
    search_pages_ok: int = 0
    search_pages_failed: int = 0
    vacancies_direct_ok: int = 0
    vacancies_direct_failed: int = 0
    vacancies_proxy_ok: int = 0
    vacancies_proxy_failed: int = 0
    proxy_race_count: int = 0
    proxy_pool_snapshot: list[dict[str, Any]] = field(default_factory=list)
    requests: list[RequestRecord] = field(default_factory=list)

    def record_request(self, record: RequestRecord) -> None:
        self.requests.append(record)

    def record_proxy_race(self) -> None:
        self.proxy_race_count += 1

    def record_search_page_result(self, success: bool) -> None:
        if success:
            self.search_pages_ok += 1
        else:
            self.search_pages_failed += 1

    def record_vacancy_direct_ok(self) -> None:
        self.vacancies_direct_ok += 1

    def record_vacancy_direct_failed(self) -> None:
        self.vacancies_direct_failed += 1

    def record_vacancy_proxy_ok(self) -> None:
        self.vacancies_proxy_ok += 1

    def record_vacancy_proxy_failed(self) -> None:
        self.vacancies_proxy_failed += 1

    def sync_proxy_timeline(
        self,
        *,
        search_started_at: float | None,
        first_found_at: float | None,
        search_finished_at: float | None,
        proxies_count: int,
        proxy_pool_snapshot: list[dict[str, Any]] | None = None,
    ) -> None:
        if search_started_at is not None:
            self.proxy_search_started_at = search_started_at
        if first_found_at is not None:
            self.proxy_first_found_at = first_found_at
        if search_finished_at is not None:
            self.proxy_search_finished_at = search_finished_at
        self.proxies_found_total = proxies_count
        if proxy_pool_snapshot is not None:
            self.proxy_pool_snapshot = proxy_pool_snapshot

    def _relative(self, ts: float | None) -> float | None:
        if ts is None:
            return None
        return round(ts - self.crawl_started_at, 3)

    def meta_summary(self) -> dict[str, Any]:
        requests_direct = sum(1 for request in self.requests if not request.via_proxy)
        requests_via_proxy = sum(1 for request in self.requests if request.via_proxy)
        vacancies_failed = self.vacancies_direct_failed + self.vacancies_proxy_failed
        pool = self.proxy_pool_snapshot
        pool_top = pool[:5]
        pool_bottom = list(reversed(pool[-5:])) if pool else []
        return {
            "proxy_mode": self.proxy_mode,
            "proxy_timeline": {
                "search_started_s": self._relative(self.proxy_search_started_at),
                "first_proxy_s": self._relative(self.proxy_first_found_at),
                "search_finished_s": self._relative(self.proxy_search_finished_at),
            },
            "proxies_found_at_end": self.proxies_found_total,
            "proxy_race_count": self.proxy_race_count,
            "proxy_pool_top": pool_top,
            "proxy_pool_bottom": pool_bottom,
            "requests_total": len(self.requests),
            "requests_direct": requests_direct,
            "requests_via_proxy": requests_via_proxy,
            "vacancies_parsed_direct": self.vacancies_direct_ok,
            "vacancies_parsed_via_proxy": self.vacancies_proxy_ok,
            "vacancies_failed": vacancies_failed,
            "search_pages_ok": self.search_pages_ok,
            "search_pages_failed": self.search_pages_failed,
        }

    def request_log(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.requests]
