"""Y Combinator company directory (public, undocumented API). Best-effort enrichment."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ..enrich.heuristics import extract_tags
from ..http import Http
from .base import RawOpportunity

API = "https://api.ycombinator.com/v0.1/companies"


class YCSource:
    name = "yc"

    def fetch(self, cfg: dict[str, Any]) -> Iterator[RawOpportunity]:
        if not cfg.get("enabled", True):
            return
        batches = cfg.get("batches") or []
        max_companies = int(cfg.get("max_companies", 200))

        with Http() as http:
            count = 0
            for batch in batches:
                page = 1
                while count < max_companies:
                    data = http.get_json(
                        API,
                        params={"page": page, "batch": batch},
                        cache_ttl=86400,
                    )
                    companies = data.get("companies", [])
                    if not companies:
                        break
                    for c in companies:
                        if count >= max_companies:
                            break
                        name = c.get("name") or "Unknown"
                        # YC companies aren't opportunities; we emit a lightweight
                        # product_problem record so they appear in the sheet for
                        # manual follow-up / ATS targeting.
                        yield RawOpportunity(
                            kind="product_problem",
                            title=f"Track {name} for openings",
                            url=(
                                c.get("website")
                                or "https://www.ycombinator.com/companies/"
                                f"{name.lower().replace(' ', '-')}"
                            ),
                            source="yc",
                            company_name=name,
                            company_domain=(
                                c.get("website", "")
                                .replace("https://", "")
                                .replace("http://", "")
                                .split("/")[0]
                                if c.get("website")
                                else None
                            ),
                            company_url=c.get("website") or "",
                            description=(
                                f"YC {', '.join(c.get('batch', [])) or 'unknown batch'}. "
                                f"{c.get('long_description') or c.get('short_description') or ''}"
                            ),
                            stack=extract_tags(
                                c.get("long_description") or c.get("short_description") or ""
                            ),
                            posted_at=None,
                            location=c.get("location", ""),
                            remote="remote" in (c.get("location", "").lower()),
                            confidence="unverified",
                            payload={"batch": c.get("batch"), "team_size": c.get("team_size")},
                        )
                        count += 1
                    page += 1
                if count >= max_companies:
                    break