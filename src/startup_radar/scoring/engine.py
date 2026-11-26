"""Scoring engine: skill match, hiring signal, contribution fit, eligibility."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

SENIOR_MARKERS = (
    "senior",
    "staff engineer",
    "principal",
    "lead engineer",
    "10+ years",
    "8+ years",
    "7+ years",
)


@dataclass
class ScoreResult:
    skill_match: float
    hiring_signal: float
    contribution_fit: float
    total: float
    band: str
    rationale: str


def _age_days(posted: datetime | None) -> int:
    if posted is None:
        return 999
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=UTC)
    return max(0, (datetime.now(UTC) - posted).days)


def _recency(days: int) -> float:
    if days <= 7:
        return 1.0
    if days <= 14:
        return 0.9
    if days <= 30:
        return 0.7
    if days <= 60:
        return 0.4
    return 0.15


def _band(total: float, bands: dict[str, Any]) -> str:
    if total >= float(bands.get("excellent", 85)):
        return "Excellent"
    if total >= float(bands.get("high", 70)):
        return "High"
    if total >= float(bands.get("medium", 55)):
        return "Medium"
    return "Low"


def compute(opp: Any, profile: dict[str, Any], scoring: dict[str, Any]) -> ScoreResult:
    weights = scoring.get("weights", {})
    w_skill = float(weights.get("skill_match", 50))
    w_hire = float(weights.get("hiring_signal", 30))
    w_contrib = float(weights.get("contribution_fit", 20))

    stack = {str(s).lower() for s in (opp.stack or [])}
    text = f"{opp.title} {opp.description or ''} {' '.join(stack)}".lower()

    profile_original = {
        str(s).lower(): str(s) for s in profile.get("demonstrated_stack", [])
    }
    profile_stack = set(profile_original)
    matched_keys = sorted(profile_stack & stack) or [
        s for s in profile_stack if s and s in text
    ]
    matched = [profile_original[key] for key in matched_keys]
    skill = w_skill * min(1.0, len(matched) / 3.0)

    days = _age_days(opp.posted_at)
    hire = w_hire * _recency(days)
    if opp.kind == "oss_issue":
        hire *= 0.8  # a live issue is not a hiring signal on its own

    labels = [str(label).lower() for label in (opp.payload or {}).get("labels", [])]
    if opp.kind == "oss_issue":
        if "good first issue" in labels:
            fit = 0.9
        elif "help wanted" in labels:
            fit = 0.75
        else:
            fit = 0.55
    elif opp.kind == "internship":
        fit = 0.8
    else:
        fit = 0.5
    contribution = w_contrib * fit

    company = getattr(opp, "company", None)
    company_remote = bool(getattr(company, "remote", False))
    location = f"{getattr(company, 'location', '') or ''} {opp.location or ''}".lower()

    eligible = True
    reasons: list[str] = []
    if scoring.get("eligibility", {}).get("exclude_senior", True):
        if any(marker in text for marker in SENIOR_MARKERS) and "intern" not in text:
            eligible = False
            reasons.append("senior-only")
    if scoring.get("eligibility", {}).get("require_remote_or_india", True):
        blob = f"{text} {location}"
        india = "india" in blob
        worldwide = any(
            marker in blob
            for marker in (
                "worldwide",
                "anywhere",
                "global",
                "any timezone",
                "remote (world)",
                "remote(world)",
            )
        )
        region_restricted = bool(
            re.search(
                r"(us|u\.s\.|uk|eu|canada|americas)\s*"
                r"(only|work authorization|based|located)",
                blob,
            )
        ) or bool(re.search(r"remote\s*[(\-]\s*(us|uk|eu|canada|americas)\b", blob))
        has_remote = company_remote or "remote" in blob
        if not (india or has_remote):
            eligible = False
            reasons.append("location-unclear")
        elif region_restricted and not india and not worldwide:
            eligible = False
            reasons.append("region-restricted")

    total = skill + hire + contribution
    if not eligible:
        total = min(total, 40.0)

    band = _band(total, scoring.get("bands", {}))
    rationale = (
        f"matched: {', '.join(matched) or 'none'}; "
        f"age: {days}d; labels: {', '.join(labels) or 'none'}; "
        f"eligible: {'yes' if eligible else 'no (' + ', '.join(reasons) + ')'}"
    )
    return ScoreResult(
        skill_match=round(skill, 1),
        hiring_signal=round(hire, 1),
        contribution_fit=round(contribution, 1),
        total=round(total, 1),
        band=band,
        rationale=rationale,
    )
