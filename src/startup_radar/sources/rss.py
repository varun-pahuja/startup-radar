"""RSS/Atom feed adapter for custom sources."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import feedparser

from ..enrich.heuristics import extract_tags
from ..http import Http, UnsafeUrl, ensure_safe_url
from .base import RawOpportunity


class RSSSource:
    name = "rss"

    def fetch(self, cfg: dict[str, Any]) -> Iterator[RawOpportunity]:
        if not cfg.get("enabled", False):
            return
        feeds = cfg.get("feeds") or []
        for entry in feeds:
            url = entry.get("url")
            if not url:
                continue
            try:
                ensure_safe_url(url)
            except UnsafeUrl:
                continue
            yield from self._parse_feed(url, entry)

    def _parse_feed(self, url: str, entry: dict[str, Any]) -> Iterator[RawOpportunity]:
        # feedparser is lenient; we use http.get_json for caching + SSRF guard
        with Http() as http:
            # Fetch as text, parse with feedparser
            resp = http._client.get(
                url,
                headers={"Accept": "application/rss+xml, application/atom+xml"},
            )
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)

        company_name = entry.get("company_name") or urlparse(url).netloc
        for item in parsed.entries:
            title = item.get("title", "Untitled")
            link = item.get("link", "")
            if not link:
                continue
            # Try to get description/summary
            desc = item.get("description") or item.get("summary") or ""
            # feedparser may have html in description
            from .hackernews import _strip_html
            text = _strip_html(desc)
            posted = None
            if "published_parsed" in item and item.published_parsed:
                posted = datetime(*item.published_parsed[:6]).replace(tzinfo=UTC)
            elif "updated_parsed" in item and item.updated_parsed:
                posted = datetime(*item.updated_parsed[:6]).replace(tzinfo=UTC)

            yield RawOpportunity(
                kind=entry.get("kind", "job"),
                title=title[:180],
                url=link,
                source="rss",
                company_name=company_name,
                company_url=url,
                description=text[:4000],
                stack=extract_tags(text),
                posted_at=posted,
                location=entry.get("location", ""),
                remote=entry.get("remote", "remote" in text.lower()),
                confidence="unverified",
                payload={"feed_url": url, "entry_id": item.get("id", "")},
            )