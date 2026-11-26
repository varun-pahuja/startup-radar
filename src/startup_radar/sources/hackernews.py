"""Hacker News "Who is hiring?" via the free Algolia API."""

from __future__ import annotations

import html
import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

from ..enrich.heuristics import extract_tags
from ..http import Http
from .base import RawOpportunity

SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
ITEM = "https://hn.algolia.com/api/v1/items"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str) -> str:
    value = value.replace("</p>", "\n").replace("<p>", "\n").replace("<br>", "\n")
    value = _TAG_RE.sub(" ", value)
    value = html.unescape(value)
    return re.sub(r"[ \t]+", " ", value).strip()


def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _segments(line: str) -> list[str]:
    return [seg.strip(" *") for seg in line.split("|") if seg.strip(" *")]


def _looks_like_candidate(first: str, text: str) -> bool:
    lowered = text.lower()
    if first.lower().startswith(("location:", "remote", "seeking", "looking")):
        return True
    candidate = (
        "i am a ",
        "i'm a ",
        "i am looking for",
        "i'm looking for",
        "my resume",
        "resume:",
        "open to work",
    )
    if any(phrase in lowered for phrase in candidate):
        return True
    closed = (
        "position has been filled",
        "no longer hiring",
        "this role is closed",
        "seeking work",
        "seeking a job",
        "looking for work",
        "willing to relocate",
    )
    return any(phrase in lowered for phrase in closed)


def _guess_location(text: str) -> str:
    if re.search(r"\bremote\b", text, re.IGNORECASE):
        return "Remote"
    match = re.search(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),\s*(?:India|US|UK|CA|EU)\b", text)
    return match.group(0) if match else ""


class HackerNewsSource:
    name = "hackernews"

    def fetch(self, cfg: dict[str, Any]) -> Iterator[RawOpportunity]:
        if not cfg.get("enabled", True):
            return
        max_age = int(cfg.get("max_age_days", 30))
        cutoff = datetime.now(UTC) - timedelta(days=max_age)

        with Http() as http:
            search = http.get_json(
                SEARCH,
                params={"tags": "story,author_whoishiring", "hitsPerPage": 6},
                cache_ttl=3600,
            )
            hits = search.get("hits", [])
            story = next(
                (h for h in hits if "who is hiring" in (h.get("title") or "").lower()),
                hits[0] if hits else None,
            )
            if story is None:
                return
            thread = http.get_json(f"{ITEM}/{story['objectID']}", cache_ttl=3600)

        for child in thread.get("children", []):
            text = _strip_html(child.get("text") or "")
            if not text:
                continue
            posted = datetime.fromtimestamp(child.get("created_at_i", 0), tz=UTC)
            if posted < cutoff:
                continue
            first_line = _first_line(text)
            if not first_line:
                continue
            segments = _segments(first_line)
            company = (segments[0] if segments else first_line)[:120] or "Unknown"
            if _looks_like_candidate(company, text):
                continue
            if any(
                word in company.lower()
                for word in ("engineer", "developer", "designer", "manager", "remote", "full-time")
            ):
                company = "Unknown"
            title = (" | ".join(segments[:3]) if segments else first_line)[:180]
            lowered = text.lower()
            yield RawOpportunity(
                kind="internship" if re.search(r"\bintern(ship)?\b", first_line, re.I) else "job",
                title=title,
                url=f"https://news.ycombinator.com/item?id={child.get('id')}",
                source="hackernews",
                company_name=company,
                description=text[:4000],
                stack=extract_tags(text),
                posted_at=posted,
                location=_guess_location(text),
                remote="remote" in lowered,
                confidence="unverified",
                payload={"author": child.get("author")},
            )
