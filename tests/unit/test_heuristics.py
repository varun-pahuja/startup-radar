"""Tests for heuristic tag extraction."""

from startup_radar.enrich.heuristics import extract_tags


def test_extracts_known_skills() -> None:
    tags = extract_tags("We use TypeScript, React, Next.js and Supabase.")
    assert "TypeScript" in tags
    assert "React" in tags
    assert "Next.js" in tags
    assert "Supabase" in tags


def test_no_false_positive_inside_words() -> None:
    # "react" must not match "reactive", "go" must not match "going"
    tags = extract_tags("reactive systems and going fast")
    assert "React" not in tags


def test_empty_text() -> None:
    assert extract_tags("") == []
