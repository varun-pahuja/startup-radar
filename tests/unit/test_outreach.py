"""Draft-only outreach: drafts build text, .eml writes a file, nothing sends."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from startup_radar.models import Base, Company, Contact, Opportunity, Outreach
from startup_radar.outreach import draft, due, export, mark_sent, record, render
from startup_radar.provenance import utcnow


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    company = Company(name="Acme", domain="acme.io", remote=True)
    session.add(company)
    session.flush()
    opp = Opportunity(
        kind="job",
        title="Founding Engineer",
        url="https://acme.io/jobs/1",
        content_hash="h1",
        company_id=company.id,
        source="yc",
        source_url="https://acme.io/jobs/1",
        stack=["Python", "FastAPI"],
    )
    session.add(opp)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _opp_id(db: Session) -> int:
    return db.query(Opportunity).one().id


def test_draft_creates_row_with_subject_and_body(db: Session) -> None:
    item = draft(db, _opp_id(db))
    assert item is not None
    assert item.subject
    assert len(item.body.split()) >= 50  # roughly in the 70-150 word band
    assert item.status == "draft"
    assert item.contact_id is None  # no published contact yet


def test_draft_is_idempotent(db: Session) -> None:
    first = draft(db, _opp_id(db))
    second = draft(db, _opp_id(db))
    assert first is not None and second is not None
    assert first.id == second.id
    assert db.query(Outreach).count() == 1


def test_draft_for_missing_opportunity_returns_none(db: Session) -> None:
    assert draft(db, 99999) is None


def test_draft_uses_published_contact(db: Session) -> None:
    company = db.query(Company).one()
    contact = Contact(company_id=company.id, email="careers@acme.io", role="careers")
    db.add(contact)
    db.commit()
    item = draft(db, _opp_id(db))
    assert item is not None
    assert item.contact_id == contact.id


def test_eml_renders_without_inventing_a_recipient(db: Session) -> None:
    item = draft(db, _opp_id(db))
    assert item is not None
    raw = render(item).decode()
    assert "Subject:" in raw
    assert "X-Startup-Radar: draft-only" in raw
    assert "\nTo:" not in raw and "\r\nTo:" not in raw


def test_eml_includes_published_address(db: Session) -> None:
    company = db.query(Company).one()
    contact = Contact(company_id=company.id, email="careers@acme.io")
    db.add(contact)
    db.commit()
    item = draft(db, _opp_id(db))
    assert item is not None
    assert "To: careers@acme.io" in render(item, contact).decode()


def test_export_writes_file(db: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    item = draft(db, _opp_id(db))
    assert item is not None
    path = export(item, None, tmp_path)
    assert path.exists()
    assert path.suffix == ".eml"
    assert b"X-Startup-Radar" in path.read_bytes()


def test_followup_schedule_and_max_two(db: Session) -> None:
    item = draft(db, _opp_id(db))
    assert item is not None
    assert due(db) == []  # not sent yet

    item.status = "sent"
    mark_sent(item)
    assert item.sent_at is not None
    assert item.followup_due is not None
    assert due(db) == []  # window not open yet

    item.followup_due = utcnow() - timedelta(days=1)
    db.commit()
    assert [r.id for r in due(db)] == [item.id]

    record(db, item.id)
    db.expire_all()
    item = db.get(Outreach, item.id)
    assert item is not None
    assert item.followup_due is not None  # second nudge scheduled
    assert due(db) == []  # not due again yet

    item.followup_due = utcnow() - timedelta(days=1)
    db.commit()
    record(db, item.id)
    db.expire_all()
    item = db.get(Outreach, item.id)
    assert item is not None
    assert item.followup_due is None  # queue closed after two
    assert due(db) == []
