"""ATS public job-board APIs: Ashby, Greenhouse, Lever, Workable."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ..enrich.heuristics import extract_tags
from ..http import Http
from .base import RawOpportunity


class ATSSource:
    name = "ats"

    def fetch(self, cfg: dict[str, Any]) -> Iterator[RawOpportunity]:
        if not cfg.get("enabled", True):
            return
        companies = cfg.get("companies") or []
        for entry in companies:
            provider = entry.get("provider", "").lower()
            slug = entry.get("slug")
            if not slug:
                continue
            yield from self._fetch_provider(provider, slug, entry)

    def _fetch_provider(
        self, provider: str, slug: str, entry: dict[str, Any]
    ) -> Iterator[RawOpportunity]:
        with Http() as http:
            if provider == "ashby":
                yield from self._ashby(http, slug, entry)
            elif provider == "greenhouse":
                yield from self._greenhouse(http, slug, entry)
            elif provider == "lever":
                yield from self._lever(http, slug, entry)
            elif provider == "workable":
                yield from self._workable(http, slug, entry)

    def _ashby(self, http: Http, slug: str, entry: dict[str, Any]) -> Iterator[RawOpportunity]:
        # https://docs.ashbyhq.com/reference/postapi-job-board
        data = http.get_json(
            f"https://api.ashbyhq.com/job-board/{slug}/jobs",
            headers={"Content-Type": "application/json"},
            cache_ttl=3600,
        )
        for job in data.get("jobs", []):
            yield RawOpportunity(
                kind="job",
                title=job.get("title", "Untitled"),
                url=job.get("jobUrl", ""),
                source="ats_ashby",
                company_name=entry.get("company_name") or slug,
                company_url=f"https://jobs.ashbyhq.com/{slug}",
                description=(job.get("descriptionPlain", "") or job.get("description", ""))[:4000],
                stack=extract_tags(job.get("descriptionPlain", "") or job.get("description", "")),
                location=job.get("locationName", ""),
                remote=job.get("isRemote", False),
                confidence="verified",
                payload={
                    "department": job.get("departmentName"),
                    "employmentType": job.get("employmentType"),
                },
            )

    def _greenhouse(self, http: Http, slug: str, entry: dict[str, Any]) -> Iterator[RawOpportunity]:
        # https://developers.greenhouse.io/job-board.html
        data = http.get_json(
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
            cache_ttl=3600,
        )
        for job in data.get("jobs", []):
            # Greenhouse doesn't include full description in list; fetch per job
            # to avoid N+1, we just store what we have and enrich later if needed.
            abs_url = job.get("absolute_url", "")
            yield RawOpportunity(
                kind="job",
                title=job.get("title", "Untitled"),
                url=abs_url,
                source="ats_greenhouse",
                company_name=entry.get("company_name") or slug,
                company_url=f"https://boards.greenhouse.io/{slug}",
                description=job.get("content", "")[:4000] or "",
                stack=extract_tags(job.get("content", "") or ""),
                location=job.get("location", {}).get("name", "") if job.get("location") else "",
                remote=job.get("metadata", {}).get("remote") == "yes",
                confidence="verified",
                payload={
                    "department": job.get("departments", [{}])[0].get("name")
                    if job.get("departments")
                    else None,
                },
            )

    def _lever(self, http: Http, slug: str, entry: dict[str, Any]) -> Iterator[RawOpportunity]:
        # https://api.lever.co/v0/postings/{company}?mode=json
        data = http.get_json(
            f"https://api.lever.co/v0/postings/{slug}",
            params={"mode": "json"},
            cache_ttl=3600,
        )
        for job in data:
            yield RawOpportunity(
                kind="job",
                title=job.get("text", "Untitled"),
                url=job.get("hostedUrl", ""),
                source="ats_lever",
                company_name=entry.get("company_name") or slug,
                company_url=f"https://jobs.lever.co/{slug}",
                description=(job.get("descriptionPlain", "") or job.get("description", ""))[:4000],
                stack=extract_tags(job.get("descriptionPlain", "") or job.get("description", "")),
                location=job.get("categories", {}).get("location", "") or "",
                remote=job.get("workplaceType", "").lower() == "remote",
                confidence="verified",
                payload={
                    "team": job.get("categories", {}).get("team"),
                    "commitment": job.get("categories", {}).get("commitment"),
                },
            )

    def _workable(self, http: Http, slug: str, entry: dict[str, Any]) -> Iterator[RawOpportunity]:
        # https://jobs.workable.com/api/v1/jobs?company={slug}
        data = http.get_json(
            "https://jobs.workable.com/api/v1/jobs",
            params={"company": slug},
            cache_ttl=3600,
        )
        for job in data.get("jobs", []):
            yield RawOpportunity(
                kind="job",
                title=job.get("title", "Untitled"),
                url=job.get("url", ""),
                source="ats_workable",
                company_name=entry.get("company_name") or slug,
                company_url=f"https://apply.workable.com/{slug}",
                description=job.get("description", "")[:4000],
                stack=extract_tags(job.get("description", "")),
                location=job.get("location", ""),
                remote=job.get("remote", False),
                confidence="verified",
                payload={"department": job.get("department"), "type": job.get("employmentType")},
            )