"""Модель одного прокси и утилиты форматирования адреса."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProxyEntry:
    """Запись прокси в пуле с накопленной статистикой успехов и провалов.

    Адрес хранится в формате ``http://host:port`` — так его ожидает requests.
    Счётчики обновляет ProxyPool после proxy race: победитель получает +success,
    остальные участники гонки — +failure.
    """

    addr: str
    failures: int = 0
    successes: int = 0


def format_addr(host: str, port: int) -> str:
    """Собирает URL прокси для requests.Session.proxies."""
    return f"http://{host}:{port}"


def host_port(proxy_addr: str) -> str:
    """Убирает схему из адреса — для логов и JSON-отчётов (host:port)."""
    return proxy_addr.removeprefix("http://").removeprefix("https://")
