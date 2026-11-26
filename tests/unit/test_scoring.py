"""Tests for the scoring engine."""

from datetime import UTC, datetime
from types import SimpleNamespace

from startup_radar.scoring import compute

PROFILE = {"demonstrated_stack": ["TypeScript", "React", "Python", "Supabase"]}
SCORING = {
    "weights": {"skill_match": 50, "hiring_signal": 30, "contribution_fit": 20},
    "bands": {"excellent": 85, "high": 70, "medium": 55},
    "eligibility": {"require_remote_or_india": True, "exclude_senior": True},
}


def _opp(**overrides):
    base = dict(
        kind="oss_issue",
        title="Fix TypeScript docs for React component",
        description="Good first issue in a remote-friendly repo.",
        stack=["TypeScript", "React"],
        posted_at=datetime.now(UTC),
        payload={"labels": ["good first issue"]},
        location="Remote",
        company=SimpleNamespace(remote=True, location="Remote"),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_strong_match_scores_high():
    result = compute(_opp(), PROFILE, SCORING)
    assert result.total >= 70
    assert result.band in {"High", "Excellent"}
    assert "TypeScript" in result.rationale


def test_senior_role_is_gated_low():
    result = compute(
        _opp(title="Senior Staff Engineer, TypeScript", payload={"labels": []}),
        PROFILE,
        SCORING,
    )
    assert result.band == "Low"
    assert result.total <= 40


def test_no_skill_overlap_scores_lower_than_overlap():
    weak = compute(_opp(title="Rust systems work", stack=["Rust"]), PROFILE, SCORING)
    strong = compute(_opp(), PROFILE, SCORING)
    assert weak.total < strong.total
