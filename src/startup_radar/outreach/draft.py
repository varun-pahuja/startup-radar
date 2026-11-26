"""Build an outreach draft from an opportunity. Draft only — never sends."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..config import profile
from ..enrich import get_adapter, is_enabled
from ..enrich.llm_enrich import draft_outreach
from ..models import ActivityLog, Company, Contact, Opportunity, Outreach

MAX_SUBJECT = 300
MAX_BODY = 2000
# Follow-ups: first after 5-7 days, second after 7-10 days, max two.
FIRST_FOLLOWUP_DAYS = 6
SECOND_FOLLOWUP_DAYS = 8
MAX_FOLLOWUPS = 2


def best_contact(session: Session, company: Company | None) -> Contact | None:
    """Prefer a contact with a real published address; else any; else None."""
    if company is None:
        return None
    contacts = (
        session.query(Contact).filter(Contact.company_id == company.id).all()
    )
    if not contacts:
        return None
    for c in contacts:
        if "@" in c.email and "." in c.email:
            return c
    return contacts[0]


def _personal_line(p: dict) -> str:
    links = p.get("links") or {}
    github = links.get("github") or ""
    site = f"https://github.com/{github}" if github else (links.get("linkedin") or "")
    return site


def _template(p: dict, opp: Opportunity, company: Company | None) -> tuple[str, str]:
    """70-150 words, one clear ask, no fluff. Works with no LLM configured."""
    name = p.get("name") or "Unknown"
    site = _personal_line(p)
    company_name = company.name if company and company.name else "Unknown"
    stack = ", ".join((opp.stack or [])[:3]) or "full-stack"
    education = p.get("education") or ""

    if opp.kind == "oss_issue":
        subject = f"Idea for {opp.title[:80]}"
        body = (
            f"Hi {company_name} team,\n\n"
            f"I read \"{opp.title}\" and I'd like to take a crack at it. "
            f"I work mostly in {stack}"
            + (f" and I'm a {education}" if education else "")
            + ".\n\n"
            f"Before I start: is a short plan posted in the issue useful, or should "
            f"I just open a small PR?\n\n"
            f"Portfolio: {site or 'Not Publicly Available'}\n\n"
            f"— {name}"
        )
    else:
        subject = f"{opp.title[:80]} — {name}"
        body = (
            f"Hi {company_name} team,\n\n"
            f"I'm {name}"
            + (f", {education}" if education else "")
            + f". I saw your posting for {opp.title} "
            f"and my background lines up: {stack}.\n\n"
            f"I've shipped full-stack work at a small team and I'm looking for a "
            f"small, fast-moving startup where I can own a slice of the product. "
            f"Remote or India works for me.\n\n"
            f"Would a 15-minute call this week be possible?\n\n"
            f"Portfolio: {site or 'Not Publicly Available'}\n\n"
            f"— {name}"
        )
    return subject[:MAX_SUBJECT], body[:MAX_BODY]


def _llm_draft(
    p: dict,
    opp: Opportunity,
    company: Company | None,
    contact: Contact | None,
) -> tuple[str, str] | None:
    if not is_enabled():
        return None
    adapter = get_adapter()
    if adapter is None:
        return None
    result = draft_outreach(
        adapter,
        opportunity_title=opp.title,
        company_name=company.name if company and company.name else "Unknown",
        contact_name=None if contact is None or contact.name == "Unknown" else contact.name,
        contact_role=None if contact is None or contact.role == "Unknown" else contact.role,
        your_profile=f"{p.get('name', 'Unknown')} — {p.get('education', '')} — "
        f"stack: {', '.join((opp.stack or [])[:5])}",
    )
    if not result:
        return None
    subject = str(result.get("subject", ""))[:MAX_SUBJECT]
    body = str(result.get("body", ""))[:MAX_BODY]
    return (subject, body) if subject and body else None


def draft(session: Session, opportunity_id: int) -> Outreach | None:
    """Create (or return the existing) draft for an opportunity."""
    opp = session.get(Opportunity, opportunity_id)
    if opp is None:
        return None
    existing = (
        session.query(Outreach)
        .filter(
            Outreach.opportunity_id == opportunity_id,
            Outreach.status.in_(("draft", "approved")),
        )
        .first()
    )
    if existing is not None:
        return existing

    company = session.get(Company, opp.company_id) if opp.company_id else None
    contact = best_contact(session, company)
    p = profile()

    parts = _llm_draft(p, opp, company, contact) or _template(p, opp, company)
    item = Outreach(
        opportunity_id=opp.id,
        contact_id=contact.id if contact else None,
        subject=parts[0],
        body=parts[1],
        status="draft",
    )
    session.add(item)
    session.add(
        ActivityLog(
            action="draft_outreach",
            entity="opportunity",
            entity_id=opp.id,
            note=parts[0][:120],
        )
    )
    session.commit()
    return item
