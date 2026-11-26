"""Public contact discovery: only addresses a company publishes itself."""

from __future__ import annotations

from startup_radar.enrich.contacts import _candidate_urls, extract_emails, is_junk, role_for
from startup_radar.models import Company

PAGE = """
<html><body>
  <a href="mailto:Careers@Acme.io">careers</a>
  <p>Press: press@acme.io.</p>
  <p>Reach us at hello@acme.io or jobs@acme.io.</p>
  <p>Template: yourname@example.com, support@sentry.io</p>
  <p>Duplicate: hello@acme.io again.</p>
</body></html>
"""


def test_extracts_published_emails() -> None:
    found = extract_emails(PAGE)
    assert "careers@acme.io" in found
    assert "press@acme.io" in found
    assert "hello@acme.io" in found
    assert "jobs@acme.io" in found


def test_drops_placeholders_and_vendors() -> None:
    found = extract_emails(PAGE)
    assert "yourname@example.com" not in found
    assert "support@sentry.io" not in found


def test_deduplicates_and_strips_punctuation() -> None:
    found = extract_emails("a@b.io. and (c@d.io)")
    assert found == ["a@b.io", "c@d.io"]


def test_is_junk_domains() -> None:
    assert is_junk("x@example.com")
    assert is_junk("x@github.com")
    assert not is_junk("x@acme.io")


def test_role_is_only_derived_from_generic_local_parts() -> None:
    assert role_for("careers@acme.io") == "careers"
    assert role_for("jobs@acme.io") == "jobs"
    # never invents a person's name from the address
    assert role_for("varun@acme.io") == "Unknown"


def test_candidate_urls_prefer_domain() -> None:
    with_domain = Company(name="Acme", domain="acme.io", url="https://jobs.ashbyhq.com/x")
    assert _candidate_urls(with_domain)[0] == "https://acme.io/"

    only_url = Company(name="Acme", url="https://acme.io/careers")
    assert _candidate_urls(only_url)[0] == "https://acme.io/"

    nowhere = Company(name="Acme")
    assert _candidate_urls(nowhere) == []
