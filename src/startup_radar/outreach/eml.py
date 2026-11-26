"""Export a draft to a standard .eml file. The user opens and sends it themselves."""

from __future__ import annotations

import re
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path

from ..config import home, profile
from ..models import Contact, Outreach

EMAIL_OK = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}$")


def _to_address(item: Outreach, contact: Contact | None) -> str:
    """Never invent an address: only a published, well-formed one is used."""
    if contact is None:
        return ""
    email = (contact.email or "").strip()
    return email if EMAIL_OK.match(email) else ""


def render(item: Outreach, contact: Contact | None = None) -> bytes:
    """Build RFC-5322 bytes for a draft. To is omitted when no address exists."""
    p = profile()
    links = p.get("links") or {}
    msg = EmailMessage(policy=SMTP)
    msg["Subject"] = item.subject or "(no subject)"
    msg["From"] = links.get("email") or "Not Publicly Available"
    to = _to_address(item, contact)
    if to:
        msg["To"] = to
    msg["X-Startup-Radar"] = "draft-only; nothing was sent by this tool"
    msg.set_content(item.body or "")
    return msg.as_bytes()


def export(
    item: Outreach,
    contact: Contact | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Write the draft to drafts/<id>-<slug>.eml and return the path."""
    target = out_dir or (home() / "drafts")
    target.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", (item.subject or "draft").lower()).strip("-")[:40]
    path = target / f"{item.id}-{slug or 'draft'}.eml"
    path.write_bytes(render(item, contact))
    return path
