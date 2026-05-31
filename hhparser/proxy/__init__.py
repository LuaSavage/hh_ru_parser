"""Пакет прокси: pool, discovery через proxybroker, фасад ``Proxy`` для scrapper."""

from .entry import ProxyEntry, format_addr, host_port
from .facade import (
    DEFAULT_PROXY_CONNECT_TIMEOUT,
    DEFAULT_PROXY_READ_TIMEOUT,
    Proxy,
)
from .pool import DEFAULT_RACE_WORKERS, ProxyPool

__all__ = [
    "DEFAULT_PROXY_CONNECT_TIMEOUT",
    "DEFAULT_PROXY_READ_TIMEOUT",
    "DEFAULT_RACE_WORKERS",
    "Proxy",
    "ProxyEntry",
    "ProxyPool",
    "format_addr",
    "host_port",
]
