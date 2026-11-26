"""Dashboard API + page tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from startup_radar.models import Opportunity, Outreach, Task


def test_overview_renders(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    r = c.get("/")
    assert r.status_code == 200
    assert "Overview" in r.text


def test_sheet_tabs_render(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    for tab in ("opportunities", "outreach", "applications", "tasks", "activity"):
        r = c.get(f"/sheet/{tab}")
        assert r.status_code == 200, tab


def test_unknown_tab_redirects(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    r = c.get("/sheet/nope", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/sheet/opportunities"


def test_detail_renders(client: tuple[TestClient, Session]) -> None:
    c, db = client
    opp = db.query(Opportunity).filter_by(content_hash="hash-good").one()
    r = c.get(f"/opportunity/{opp.id}")
    assert r.status_code == 200
    assert "Fix TypeScript docs" in r.text


def test_detail_missing_is_404(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    assert c.get("/opportunity/99999").status_code == 404


def test_patch_opportunity_status_persists(client: tuple[TestClient, Session]) -> None:
    c, db = client
    opp = db.query(Opportunity).filter_by(content_hash="hash-good").one()
    r = c.patch(f"/api/opportunities/{opp.id}", data={"status": "shortlisted"})
    assert r.status_code == 204
    db.expire_all()
    assert db.get(Opportunity, opp.id).status == "shortlisted"


def test_patch_opportunity_rejects_bad_status(client: tuple[TestClient, Session]) -> None:
    c, db = client
    opp = db.query(Opportunity).filter_by(content_hash="hash-good").one()
    r = c.patch(f"/api/opportunities/{opp.id}", data={"status": "hacked"})
    assert r.status_code == 422


def test_patch_opportunity_rejects_long_notes(client: tuple[TestClient, Session]) -> None:
    c, db = client
    opp = db.query(Opportunity).filter_by(content_hash="hash-good").one()
    r = c.patch(f"/api/opportunities/{opp.id}", data={"notes": "x" * 6000})
    assert r.status_code == 422


def test_task_lifecycle(client: tuple[TestClient, Session]) -> None:
    c, db = client
    r = c.post("/api/tasks", data={"title": "Read the docs"}, follow_redirects=False)
    assert r.status_code == 303
    task = db.query(Task).filter_by(title="Read the docs").one()

    assert c.patch(f"/api/tasks/{task.id}", data={"status": "done"}).status_code == 204
    db.expire_all()
    assert db.get(Task, task.id).status == "done"

    assert c.patch(f"/api/tasks/{task.id}", data={"status": "bogus"}).status_code == 422

    assert c.delete(f"/api/tasks/{task.id}").status_code == 200
    db.expire_all()
    assert db.get(Task, task.id) is None


def test_patch_outreach_rejects_bad_status(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    r = c.patch("/api/outreach/1", data={"status": "sent-ish"})
    assert r.status_code == 422


def test_create_outreach_draft_redirects(client: tuple[TestClient, Session]) -> None:
    c, db = client
    opp = db.query(Opportunity).filter_by(content_hash="hash-good").one()
    r = c.post("/api/outreach", data={"opportunity_id": opp.id}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/sheet/outreach"
    db.expire_all()
    item = db.query(Outreach).filter_by(opportunity_id=opp.id).one()
    assert item.status == "draft"
    assert item.subject


def test_create_outreach_unknown_opportunity_is_404(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    assert c.post("/api/outreach", data={"opportunity_id": 99999}).status_code == 404


def test_outreach_eml_download_is_draft_only(client: tuple[TestClient, Session]) -> None:
    c, db = client
    item = db.query(Outreach).one()
    r = c.get(f"/api/outreach/{item.id}/eml")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("message/rfc822")
    assert "attachment" in r.headers["content-disposition"]
    assert b"X-Startup-Radar: draft-only" in r.content


def test_eml_download_missing_is_404(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    assert c.get("/api/outreach/99999/eml").status_code == 404


def test_marking_sent_queues_a_followup(client: tuple[TestClient, Session]) -> None:
    c, db = client
    item = db.query(Outreach).one()
    assert c.patch(f"/api/outreach/{item.id}", data={"status": "sent"}).status_code == 204
    db.expire_all()
    item = db.get(Outreach, item.id)
    assert item is not None
    assert item.sent_at is not None
    assert item.followup_due is not None


def test_followup_endpoint_records_and_closes_queue(client: tuple[TestClient, Session]) -> None:
    c, db = client
    item = db.query(Outreach).one()
    c.patch(f"/api/outreach/{item.id}", data={"status": "sent"})
    for _ in range(2):
        assert c.post(f"/api/outreach/{item.id}/followup").status_code == 204
    db.expire_all()
    item = db.get(Outreach, item.id)
    assert item is not None
    assert item.followup_due is None


def test_followup_unknown_is_404(client: tuple[TestClient, Session]) -> None:
    c, _ = client
    assert c.post("/api/outreach/99999/followup").status_code == 404
