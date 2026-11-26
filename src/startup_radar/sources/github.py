"""GitHub good-first-issue discovery via the Search API."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

from ..config import get_settings
from ..enrich.heuristics import extract_tags
from ..http import Http
from .base import RawOpportunity

API = "https://api.github.com"


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = get_settings().github_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class GitHubSource:
    name = "github"

    def fetch(self, cfg: dict[str, Any]) -> Iterator[RawOpportunity]:
        if not cfg.get("enabled", True):
            return
        labels = cfg.get("labels") or ["good first issue"]
        label = labels[0]
        max_per_org = int(cfg.get("max_per_org", 10))
        max_age = int(cfg.get("max_age_days", 45))
        since = (datetime.now(UTC) - timedelta(days=max_age)).strftime("%Y-%m-%d")

        with Http() as http:
            for org in cfg.get("orgs") or []:
                query = f'user:{org} is:issue is:open updated:>={since} label:"{label}"'
                data = http.get_json(
                    f"{API}/search/issues",
                    headers=_headers(),
                    params={
                        "q": query,
                        "sort": "updated",
                        "order": "desc",
                        "per_page": max_per_org,
                    },
                    cache_ttl=3600,
                )
                for item in data.get("items", [])[:max_per_org]:
                    yield self._to_raw(org, item)

    @staticmethod
    def _to_raw(org: str, item: dict[str, Any]) -> RawOpportunity:
        repo = item.get("repository_url", "").split("/repos/")[-1] or org
        labels = [label.get("name", "") for label in item.get("labels", [])]
        text = f"{item.get('title', '')}\n{item.get('body', '') or ''}"
        tags = extract_tags(text)
        if repo:
            tags.append(repo.split("/")[0])
        return RawOpportunity(
            kind="oss_issue",
            title=item.get("title", "Untitled issue"),
            url=item.get("html_url", ""),
            source="github",
            company_name=repo.split("/")[0] if repo else org,
            company_url=f"https://github.com/{repo.split('/')[0]}" if repo else "",
            description=(item.get("body") or "")[:2000],
            stack=sorted(set(tags)),
            posted_at=_parse_iso(item.get("created_at")),
            remote=True,
            confidence="verified",
            payload={"repo": repo, "labels": labels, "comments": item.get("comments", 0)},
        )
