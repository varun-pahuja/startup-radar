"""HTTP client with retry-friendly defaults and an on-disk JSON cache."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import data_dir

USER_AGENT = "startup-radar/0.1 (+https://github.com/varun-pahuja)"
MAX_TEXT_BYTES = 500_000


class UnsafeUrl(ValueError):
    """Raised when a URL could reach a local or non-HTTP target (SSRF guard)."""


def ensure_safe_url(url: str) -> None:
    """Reject non-HTTP(S) schemes and literal private/loopback hosts.

    Defence-in-depth for config-supplied URLs (RSS, ATS, org slugs). Hostnames
    are allowed; DNS names that *resolve* to private IPs are not caught here.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrl(f"blocked scheme: {parsed.scheme or 'none'}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise UnsafeUrl("missing host")
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        raise UnsafeUrl("blocked local host")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return  # not an IP literal; allow the hostname
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        raise UnsafeUrl("blocked private/loopback address")


class Http:
    def __init__(self, timeout: float = 20.0) -> None:
        self._client = httpx.Client(
            timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Http:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        cache_ttl: int = 0,
    ) -> Any:
        ensure_safe_url(url)
        cache_file = None
        if cache_ttl > 0:
            key = hashlib.sha256(
                (url + json.dumps(params or {}, sort_keys=True)).encode()
            ).hexdigest()
            cache_dir = data_dir() / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{key}.json"
            if cache_file.exists() and time.time() - cache_file.stat().st_mtime < cache_ttl:
                return json.loads(cache_file.read_text())

        resp = self._client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        if cache_file is not None:
            cache_file.write_text(json.dumps(data))
        return data

    def get_text(self, url: str, *, headers: dict[str, str] | None = None) -> str:
        """Fetch a page as text (contact discovery, RSS-adjacent reads).

        Same SSRF guard as get_json. Non-text responses yield "". Capped at
        MAX_TEXT_BYTES so a hostile host can't fill memory.
        """
        ensure_safe_url(url)
        resp = self._client.get(url, headers=headers)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "").lower()
        if ctype and not any(t in ctype for t in ("text/", "html", "xml", "json")):
            return ""
        raw = resp.content[:MAX_TEXT_BYTES]
        return raw.decode(resp.encoding or "utf-8", errors="replace")
