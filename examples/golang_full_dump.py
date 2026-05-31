#!/usr/bin/env python3
"""Fetch all golang vacancies: search pages + full vacancy pages (adaptive proxy).

Usage:
    python examples/golang_full_dump.py
    python examples/golang_full_dump.py --max-pages 1 --max-vacancies 5
    python examples/golang_full_dump.py --output output/golang.json
    python examples/golang_full_dump.py --use-proxy never
    python examples/golang_full_dump.py --request-log output/requests.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

from hhparser import VacancyScrapper, configure_logging
from hhparser.scrapper import UseProxyMode
from hhparser.template_parser import DumpParser

logger = logging.getLogger(__name__)

DEFAULT_QUERY = "golang"
DEFAULT_OUTPUT = Path("output/golang_vacancies.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dump full hh.ru vacancy JSON for a search query (adaptive proxy)."
    )
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Search text (default: golang)")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit search pages (default: all pages from hh.ru)",
    )
    parser.add_argument(
        "--max-vacancies",
        type=int,
        default=None,
        help="Limit vacancy detail pages to fetch (default: all found in search)",
    )
    parser.add_argument(
        "--use-proxy",
        choices=["always", "never", "adaptive"],
        default="adaptive",
        help="Proxy mode (default: adaptive)",
    )
    parser.add_argument(
        "--proxy-timeout",
        type=int,
        default=5,
        help="Proxy read timeout in seconds (default: 5)",
    )
    parser.add_argument(
        "--proxy-race-workers",
        type=int,
        default=8,
        help="Concurrent proxies per race (default: 8)",
    )
    parser.add_argument(
        "--include-request-log",
        action="store_true",
        help="Embed full request_log array into output JSON",
    )
    parser.add_argument(
        "--request-log",
        type=Path,
        default=None,
        help="Write request log as JSONL to this path",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level for hhparser",
    )
    return parser.parse_args()


def collect_vacancy_ids(scrapper: VacancyScrapper, page_count: int) -> list[int]:
    vacancy_ids: list[int] = []
    seen: set[int] = set()

    for page_number in range(page_count):
        page_started = time.monotonic()
        vacancies = []
        while not vacancies:
            page = scrapper.get_searching_results_page(
                page_number=page_number,
                page_count=page_count,
            )
            if page is None:
                scrapper.stats.record_search_page_result(False)
                continue
            vacancies = DumpParser.parse_search_page(page)
            if vacancies:
                scrapper.stats.record_search_page_result(True)

        new_ids = 0
        for vacancy in vacancies:
            vacancy_id = int(vacancy["id"])
            if vacancy_id not in seen:
                seen.add(vacancy_id)
                vacancy_ids.append(vacancy_id)
                new_ids += 1

        logger.info(
            "Search page %s/%s: %s vacancies, %s new ids (%.1fs)",
            page_number + 1,
            page_count,
            len(vacancies),
            new_ids,
            time.monotonic() - page_started,
        )

    return vacancy_ids


def fetch_vacancy_details(
    scrapper: VacancyScrapper,
    vacancy_ids: list[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    vacancies: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    total = len(vacancy_ids)
    for index, vacancy_id in enumerate(vacancy_ids, start=1):
        started = time.monotonic()
        page = scrapper.get_vacancy_page(id=str(vacancy_id))
        if page is None:
            error_message = "Failed to fetch vacancy page"
            errors.append({"id": vacancy_id, "error": error_message})
            logger.warning(
                "Vacancy %s/%s id=%s failed: %s (%.1fs)",
                index,
                total,
                vacancy_id,
                error_message,
                time.monotonic() - started,
            )
            continue

        try:
            vacancy = DumpParser.parse_vacancy_page(page)
            vacancies.append(vacancy)
            logger.info(
                "Vacancy %s/%s id=%s name=%r (%.1fs)",
                index,
                total,
                vacancy_id,
                vacancy.get("name", "")[:60],
                time.monotonic() - started,
            )
        except Exception as exc:
            errors.append({"id": vacancy_id, "error": str(exc)})
            logger.warning(
                "Vacancy %s/%s id=%s parse failed: %s (%.1fs)",
                index,
                total,
                vacancy_id,
                exc,
                time.monotonic() - started,
            )

    return vacancies, errors


def write_request_log(path: Path, request_log: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as log_file:
        for entry in request_log:
            log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    log_level = getattr(logging, args.log_level)
    configure_logging(log_level)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    timings: dict[str, float] = {}
    total_started = time.monotonic()

    use_proxy: UseProxyMode = args.use_proxy
    logger.info("Initializing VacancyScrapper use_proxy=%s", use_proxy)
    init_started = time.monotonic()
    scrapper = VacancyScrapper(
        params={
            "clusters": True,
            "ored_clusters": True,
            "enable_snippets": True,
            "text": args.query,
            "page": 0,
        },
        use_proxy=use_proxy,
        proxy_timeout=args.proxy_timeout,
        proxy_race_workers=args.proxy_race_workers,
    )
    timings["scrapper_init"] = time.monotonic() - init_started
    proxies_count = scrapper.proxy.count() if scrapper.proxy else 0
    logger.info("Scrapper ready in %.1fs, proxies=%s", timings["scrapper_init"], proxies_count)

    search_started = time.monotonic()
    page_count = scrapper.get_page_count()
    if args.max_pages is not None:
        page_count = min(page_count, args.max_pages)
    logger.info("Search query=%r, pages to crawl=%s", args.query, page_count)

    vacancy_ids = collect_vacancy_ids(scrapper, page_count)
    if args.max_vacancies is not None:
        vacancy_ids = vacancy_ids[: args.max_vacancies]
    timings["search_crawl"] = time.monotonic() - search_started
    logger.info(
        "Search done: %s unique vacancy ids in %.1fs",
        len(vacancy_ids),
        timings["search_crawl"],
    )

    details_started = time.monotonic()
    vacancies, errors = fetch_vacancy_details(scrapper, vacancy_ids)
    timings["vacancy_pages"] = time.monotonic() - details_started

    scrapper._sync_proxy_stats()
    stats_meta = scrapper.stats.meta_summary()
    request_log = scrapper.stats.request_log()

    write_started = time.monotonic()
    payload: dict[str, Any] = {
        "meta": {
            "query": args.query,
            "search_pages_crawled": page_count,
            "vacancy_ids_found": len(vacancy_ids),
            "vacancies_parsed": len(vacancies),
            "errors_count": len(errors),
            **stats_meta,
            "timings_seconds": {
                **timings,
                "write_json": 0.0,
                "total": 0.0,
            },
        },
        "vacancies": vacancies,
        "errors": errors,
    }
    if args.include_request_log:
        payload["request_log"] = request_log

    timings["write_json"] = time.monotonic() - write_started
    timings["total"] = time.monotonic() - total_started
    payload["meta"]["timings_seconds"]["write_json"] = timings["write_json"]
    payload["meta"]["timings_seconds"]["total"] = timings["total"]

    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, ensure_ascii=False, indent=2)

    if args.request_log is not None:
        write_request_log(args.request_log, request_log)
        logger.info("Request log saved to %s (%s entries)", args.request_log, len(request_log))

    proxy_timeline = stats_meta.get("proxy_timeline", {})
    first_proxy_s = proxy_timeline.get("first_proxy_s")
    logger.info(
        "Done query=%s vacancies=%s/%s errors=%s direct_ok=%s proxy_ok=%s proxies=%s "
        "broker_first_proxy=%ss total=%.1fs",
        args.query,
        len(vacancies),
        len(vacancy_ids),
        len(errors),
        stats_meta.get("vacancies_parsed_direct", 0),
        stats_meta.get("vacancies_parsed_via_proxy", 0),
        stats_meta.get("proxies_found_at_end", 0),
        first_proxy_s if first_proxy_s is not None else "n/a",
        timings["total"],
    )
    logger.info("Saved %s vacancies to %s", len(vacancies), args.output)
    logger.info(
        "Timings (s): init=%.1f search=%.1f vacancies=%.1f write=%.1f total=%.1f",
        timings["scrapper_init"],
        timings["search_crawl"],
        timings["vacancy_pages"],
        timings["write_json"],
        timings["total"],
    )
    return 1 if errors and not vacancies else 0


if __name__ == "__main__":
    raise SystemExit(main())
