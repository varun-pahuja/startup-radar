"""Source adapters. Add a new source here and it joins the pipeline."""

from __future__ import annotations

from typing import Any

from .ats import ATSSource
from .base import RawOpportunity, Source
from .github import GitHubSource
from .hackernews import HackerNewsSource
from .rss import RSSSource
from .yc import YCSource

__all__ = [
    "RawOpportunity",
    "Source",
    "GitHubSource",
    "HackerNewsSource",
    "YCSource",
    "ATSSource",
    "RSSSource",
    "all_sources",
]


def all_sources(cfg: dict[str, Any]) -> list[Source]:
    sources: list[Source] = []
    if (cfg.get("github") or {}).get("enabled", True):
        sources.append(GitHubSource())
    if (cfg.get("hackernews") or {}).get("enabled", True):
        sources.append(HackerNewsSource())
    if (cfg.get("yc") or {}).get("enabled", True):
        sources.append(YCSource())
    if (cfg.get("ats") or {}).get("enabled", True):
        sources.append(ATSSource())
    if (cfg.get("rss") or {}).get("enabled", False):
        sources.append(RSSSource())
    return sources
