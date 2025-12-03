"""
Utilities for determining the real client IP address.

Only trusts X-Forwarded-For headers from explicitly configured proxies.
Falls back to the direct socket address when the request does not come
through a trusted proxy.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Set

from fastapi import Request

DEFAULT_TRUSTED_PROXIES = {"127.0.0.1", "::1"}


@lru_cache(maxsize=1)
def _trusted_proxies() -> Set[str]:
    """Return the configured set of trusted proxy IPs."""
    raw = os.getenv("DSA110_TRUSTED_PROXIES", "")
    proxies = set(DEFAULT_TRUSTED_PROXIES)
    if raw:
        for entry in raw.split(","):
            entry = entry.strip()
            if entry:
                proxies.add(entry)
    return proxies


def get_client_ip(request: Request) -> str:
    """
    Determine the client IP, honoring X-Forwarded-For only for trusted proxies.
    """
    client_host = request.client.host if request.client else "0.0.0.0"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for and client_host in _trusted_proxies():
        original = forwarded_for.split(",")[0].strip()
        if original:
            return original
    return client_host
