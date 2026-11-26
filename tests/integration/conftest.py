"""Shared fixtures for dashboard integration tests (in-memory SQLite)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from startup_radar.models import Base, Company, Opportunity, Outreach, Score, Task
from startup_radar.web.app import create_app
from startup_radar.web.deps import get_db


@pytest.fixture
def client() -> Iterator[tuple[TestClient, Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()

    company = Company(name="Acme", remote=True)
    session.add(company)
    session.flush()

    good = Opportunity(
        kind="oss_issue",
        title="Fix TypeScript docs",
        url="https://example.com/issues/1",
        content_hash="hash-good",
        company_id=company.id,
        source="github",
        source_url="https://example.com/issues/1",
        status="new",
    )
    evil = Opportunity(
        kind="job",
        title="<script>alert(1)</script>",
        url="javascript:alert(1)",
        content_hash="hash-evil",
        source="hackernews",
        source_url="javascript:alert(1)",
        status="new",
    )
    session.add_all([good, evil])
    session.flush()
    session.add_all(
        [
            Score(opportunity_id=good.id, skill_match=40, hiring_signal=25,
                  contribution_fit=18, total=83, band="High", rationale="TypeScript"),
            Score(opportunity_id=evil.id, skill_match=10, hiring_signal=10,
                  contribution_fit=5, total=25, band="Low", rationale="none"),
            Task(title="Follow up"),
            Outreach(subject="Hello", body="Draft", status="draft"),
        ]
    )
    session.commit()

    app = create_app()

    def override() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), session
    finally:
        session.close()
        engine.dispose()
