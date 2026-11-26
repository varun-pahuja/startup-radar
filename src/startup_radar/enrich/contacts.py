"""Public contact discovery (Phase 4b).

Reads only what a company publishes on its own site: `mailto:` links and
plain email addresses on the homepage, /contact, /careers, /jobs.

Rules (see docs/sources-policy.md):
- No guessed emails, no pattern guessing from names, no people-search sites.
- No PII harvesting: we store a business address with its page as evidence.
- Every row carries source_url + fetched_at + confidence=unverified, because
  published ≠ deliverable.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from rich.console import Console
from sqlalchemy.orm import Session

from ..db import get_session, init_db
from ..http import Http
from ..models import ActivityLog, Company, Contact
from ..provenance import Confidence, utcnow

console = Console()

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}")
MAILTO_RE = re.compile(r"mailto:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24})", re.I)

# Placeholders, registries, vendors, and platforms — never a real contact, and
# never treated as a company's own site to scan.
JUNK_DOMAINS = frozenset(
    {
        "example.com",
        "example.org",
        "example.net",
        "test.com",
        "test.org",
        "email.com",
        "domain.com",
        "yoursite.com",
        "yourdomain.com",
        "yourcompany.com",  # template placeholder
        "sentry.io",
        "wixpress.com",
        "godaddy.com",
        "namecheap.com",
        "wordpress.com",
        "w3.org",
        "schema.org",
        "googleapis.com",
        "githubusercontent.com",
        "github.com",
        "linkedin.com",
        "twitter.com",
        "x.com",
    }
)

# Local parts that name a role, not a person. Used only to label the contact;
# anything else keeps the model default "Unknown".
GENERIC_ROLES = frozenset(
    {
        "jobs",
        "careers",
        "hiring",
        "talent",
        "apply",
        "work",
        "info",
        "hello",
        "hi",
        "team",
        "founders",
        "founder",
        "contact",
        "support",
        "press",
        "people",
        "hr",
        "events",
    }
)

# Site-relative pages worth reading, in order. "" = homepage.
PAGES = ("", "contact", "careers", "jobs")
MAX_PAGES = 4


def is_junk(email: str) -> bool:
    domain = email.rsplit("@", 1)[-1].lower()
    if domain in JUNK_DOMAINS:
        return True
    local = email.split("@", 1)[0].lower()
    # obvious template leftovers
    return local in {"yourname", "firstname", "name", "user", "someone"}


def extract_emails(text: str) -> list[str]:
    """Ordered, de-duplicated, junk-filtered emails found in a page."""
    found: list[str] = []
    for match in MAILTO_RE.findall(text) + EMAIL_RE.findall(text):
        email = match.strip().rstrip(".,;:)>]").lower()
        if is_junk(email) or email in found:
            continue
        found.append(email)
    return found


def role_for(email: str) -> str:
    """Derive a role label from the address itself — never invent a person."""
    local = email.split("@", 1)[0].lower()
    return local if local in GENERIC_ROLES else "Unknown"


def _candidate_urls(company: Company) -> list[str]:
    """Homepage plus common contact pages, derived from domain/url."""
    base = ""
    if company.domain:
        base = f"https://{company.domain}"
    elif company.url:
        parsed = urlparse(company.url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            base = f"{parsed.scheme}://{parsed.netloc}"
    if not base:
        return []
    host = urlparse(base).hostname or ""
    if host.lower() in JUNK_DOMAINS:  # github.com etc. are not company sites
        return []
    return [urljoin(base + "/", page) for page in PAGES[:MAX_PAGES]]


def discover_company(session: Session, http: Http, company: Company) -> int:
    """Find published emails for one company. Returns new contact rows."""
    if company is None or not _candidate_urls(company):
        return 0
    existing = {
        c.email.lower()
        for c in session.query(Contact).filter(Contact.company_id == company.id).all()
    }
    added = 0
    for url in _candidate_urls(company):
        try:
            page = http.get_text(url)
        except Exception:  # noqa: BLE001 - one bad page must not stop the run
            continue
        for email in extract_emails(page):
            if email in existing:
                continue
            session.add(
                Contact(
                    company_id=company.id,
                    role=role_for(email),
                    email=email,
                    source_url=url,
                    confidence=Confidence.UNVERIFIED.value,
                    fetched_at=utcnow(),
                )
            )
            existing.add(email)
            added += 1
        if added:
            break  # homepage was enough; stop hammering the site
    return added


def discover(limit: int | None = None) -> int:
    """Scan companies that have a site but no published contact yet."""
    init_db()
    session = get_session()
    added = 0
    try:
        with Http() as http:
            companies = (
                session.query(Company)
                .outerjoin(Contact, Contact.company_id == Company.id)
                .filter(Contact.id.is_(None))
                # companies with their own domain first; GitHub orgs have none
                .order_by(Company.domain.is_(None), Company.id)
                .limit(limit or 300)
                .all()
            )
            for company in companies:
                found = discover_company(session, http, company)
                if found:
                    session.commit()
                    added += found
                    console.print(f"[cyan]{company.name}[/cyan]: +{found} contact(s)")
        if added:
            session.add(ActivityLog(action="contacts", note=f"+{added} published emails"))
            session.commit()
    finally:
        session.close()
    console.print(f"[green]contacts done[/green]: {added} new")
    return added
