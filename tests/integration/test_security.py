"""Security regression tests: headers, escaping, validation, SSRF guard."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from startup_radar.http import UnsafeUrl, ensure_safe_url


def test_security_headers_present(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    r = c.get("/")
    h = r.headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "no-referrer"
    assert "camera=()" in h["permissions-policy"]
    assert h["cross-origin-opener-policy"] == "same-origin"
    assert h["cache-control"] == "no-store"
    csp = h["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "script-src 'self'" in csp
    # No CDN / inline script allowance.
    assert "unsafe-inline" not in csp


def test_scraped_title_is_escaped(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    html = c.get("/sheet/opportunities").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_dangerous_url_scheme_is_neutralised(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    html = c.get("/sheet/opportunities").text
    assert "javascript:" not in html


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost:8000/",
        "http://10.0.0.1/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "ftp://example.com/x",
    ],
)
def test_ssrf_guard_blocks(url: str) -> None:
    with pytest.raises(UnsafeUrl):
        ensure_safe_url(url)


def test_ssrf_guard_allows_public_https() -> None:
    ensure_safe_url("https://api.github.com/search/issues")
    ensure_safe_url("https://hn.algolia.com/api/v1/search")


def test_oversized_request_is_rejected(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    r = c.post("/api/tasks", data={"title": "x" * 1_100_000})
    assert r.status_code == 413
