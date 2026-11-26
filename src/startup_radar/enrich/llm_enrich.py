"""LLM-based enrichment tasks (skills, summary, outreach drafts)."""

from __future__ import annotations

from typing import Any, cast

from .llm import LLMAdapter, LLMCostExceeded

ENRICH_SCHEMA = {
    "name": "opportunity_enrichment",
    "schema": {
        "type": "object",
        "properties": {
            "skills": {"type": "array", "items": {"type": "string"}},
            "seniority": {
                "type": "string",
                "enum": ["junior", "mid", "senior", "staff", "lead", "unknown"],
            },
            "summary": {"type": "string", "maxLength": 500},
            "is_remote_friendly": {"type": "boolean"},
            "visa_sponsorship_likely": {"type": "boolean"},
        },
        "required": [
            "skills",
            "seniority",
            "summary",
            "is_remote_friendly",
            "visa_sponsorship_likely",
        ],
        "additionalProperties": False,
    },
}


OUTREACH_SCHEMA = {
    "name": "outreach_draft",
    "schema": {
        "type": "object",
        "properties": {
            "subject": {"type": "string", "maxLength": 300},
            "body": {"type": "string", "maxLength": 2000},
        },
        "required": ["subject", "body"],
        "additionalProperties": False,
    },
}


def enrich_opportunity(
    adapter: LLMAdapter,
    title: str,
    description: str,
    stack: list[str],
    location: str,
    remote: bool,
) -> dict[str, Any] | None:
    """Enrich an opportunity with LLM-extracted fields. Returns None on failure."""
    system = (
        "You analyse startup job/internship/OSS postings. "
        "Return ONLY valid JSON matching the schema. "
        "Be concise. Use 'unknown' for seniority if unclear."
    )
    user = (
        f"Title: {title}\n"
        f"Description: {description[:3000]}\n"
        f"Stack (heuristics): {stack}\n"
        f"Location: {location or 'unknown'}\n"
        f"Remote: {remote}"
    )
    try:
        return cast(
            dict[str, Any],
            adapter.complete(system, user, json_schema=ENRICH_SCHEMA, max_tokens=600),
        )
    except LLMCostExceeded:
        return None
    except Exception:
        return None


def draft_outreach(
    adapter: LLMAdapter,
    opportunity_title: str,
    company_name: str,
    contact_name: str | None,
    contact_role: str | None,
    your_profile: str,
) -> dict[str, Any] | None:
    """Draft a cold outreach email. Returns None on failure."""
    system = (
        "You write concise, professional cold outreach emails (70-150 words). "
        "No fluff. One clear ask. Return ONLY valid JSON matching the schema."
    )
    user = (
        f"Opportunity: {opportunity_title}\n"
        f"Company: {company_name}\n"
        f"Contact: {contact_name or 'Unknown'} ({contact_role or 'Unknown role'})\n"
        f"Your profile: {your_profile}\n"
        "Draft a short email introducing yourself and asking for a brief chat."
    )
    try:
        return cast(
            dict[str, Any],
            adapter.complete(system, user, json_schema=OUTREACH_SCHEMA, max_tokens=400),
        )
    except LLMCostExceeded:
        return None
    except Exception:
        return None


def summarize_company(
    adapter: LLMAdapter,
    company_name: str,
    description: str,
    website: str | None,
) -> str | None:
    """Summarise a company in 2-3 sentences. Returns None on failure."""
    system = (
        "Summarise the company in 2-3 sentences for a job seeker. "
        "Focus on what they do, stage, and tech. Return plain text (no JSON)."
    )
    user = (
        f"Company: {company_name}\n"
        f"Description: {description[:2000]}\n"
        f"Website: {website or 'unknown'}"
    )
    try:
        return cast(str, adapter.complete(system, user, max_tokens=200))
    except LLMCostExceeded:
        return None
    except Exception:
        return None