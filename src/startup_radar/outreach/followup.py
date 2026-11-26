"""Follow-up queue (draft-only).

The tool never sends anything, so a follow-up is due when *you* marked the
outreach as sent from your own mail client. First nudge after 5-7 days,
second after 7-10 days, max two — then the queue stops nagging.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from ..models import ActivityLog, Outreach
from ..provenance import utcnow
from .draft import FIRST_FOLLOWUP_DAYS, MAX_FOLLOWUPS, SECOND_FOLLOWUP_DAYS


def _aware(dt: datetime) -> datetime:
    """SQLite hands back naive UTC; keep comparisons apples-to-apples."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def followup_count(session: Session, outreach_id: int) -> int:
    return (
        session.query(ActivityLog)
        .filter(
            ActivityLog.action == "followup",
            ActivityLog.entity == "outreach",
            ActivityLog.entity_id == outreach_id,
        )
        .count()
    )


def mark_sent(item: Outreach) -> None:
    """Called when status flips to 'sent': stamp it and queue follow-up #1."""
    if item.sent_at is None:
        item.sent_at = utcnow()
    if item.followup_due is None:
        item.followup_due = utcnow() + timedelta(days=FIRST_FOLLOWUP_DAYS)


def due(session: Session) -> list[Outreach]:
    """Sent outreach whose follow-up window has opened, capped at MAX_FOLLOWUPS."""
    now = utcnow()
    rows = (
        session.query(Outreach)
        .filter(Outreach.status == "sent", Outreach.followup_due.is_not(None))
        .order_by(Outreach.followup_due)
        .all()
    )
    return [
        r
        for r in rows
        if _aware(r.followup_due) <= now  # type: ignore[arg-type]
        and followup_count(session, r.id) < MAX_FOLLOWUPS
    ]


def record(session: Session, outreach_id: int) -> Outreach | None:
    """Log one follow-up for a sent outreach. Schedules the second, then clears the queue."""
    item = session.get(Outreach, outreach_id)
    if item is None or item.status != "sent":
        return None
    count = followup_count(session, outreach_id) + 1
    session.add(
        ActivityLog(
            action="followup",
            entity="outreach",
            entity_id=outreach_id,
            note=f"follow-up {count} of {MAX_FOLLOWUPS}",
        )
    )
    if count < MAX_FOLLOWUPS:
        item.followup_due = utcnow() + timedelta(days=SECOND_FOLLOWUP_DAYS)
    else:
        item.followup_due = None
    session.commit()
    return item
