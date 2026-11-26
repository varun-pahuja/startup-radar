#!/usr/bin/env python3
"""Seed the database with a few demo opportunities for quick testing.

Run: uv run python scripts/seed.py
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from startup_radar.db import get_session, init_db
from startup_radar.models import (
    Company,
    Contact,
    Opportunity,
    Outreach,
    ProofOfWork,
    Score,
    Task,
)


def _content_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def seed(session: Session) -> None:
    # Companies
    acme = Company(
        name="Acme Corp",
        domain="acme.example.com",
        description="Open-source developer tools",
        stage="Series A",
        size="20",
        location="Remote",
        remote=True,
        url="https://acme.example.com",
        confidence="verified",
    )
    beta = Company(
        name="Beta Labs",
        domain="beta.example.com",
        description="AI-powered code review",
        stage="Seed",
        size="8",
        location="SF / Remote",
        remote=True,
        url="https://beta.example.com",
        confidence="verified",
    )
    session.add_all([acme, beta])
    session.flush()

    # Contacts
    contacts = [
        Contact(
            company_id=acme.id,
            name="Alex Chen",
            role="Founder",
            email="alex@acme.example.com",
        ),
        Contact(
            company_id=acme.id,
            name="Sam Rivera",
            role="Engineering Lead",
            email="sam@acme.example.com",
        ),
        Contact(
            company_id=beta.id,
            name="Priya Patel",
            role="CTO",
            email="priya@beta.example.com",
        ),
    ]
    session.add_all(contacts)
    session.flush()

    now = datetime.now(UTC)

    # Opportunities
    opps = [
        Opportunity(
            company_id=acme.id,
            kind="job",
            title="Founding Engineer (Full-Stack)",
            description=(
                "We're looking for a founding engineer to own the core product. "
                "Stack: Python, FastAPI, React, PostgreSQL. "
                "Remote-first, 20-50% travel for team meetups."
            ),
            url="https://acme.example.com/jobs/founding-engineer",
            content_hash=_content_hash("https://acme.example.com/jobs/founding-engineer"),
            stack=["Python", "FastAPI", "React", "PostgreSQL", "TypeScript"],
            location="Remote",
            remote=True,
            posted_at=now - timedelta(days=5),
            source="yc",
            source_url="https://api.ycombinator.com/v0.1/companies/acme",
            confidence="verified",
        ),
        Opportunity(
            company_id=acme.id,
            kind="internship",
            title="Software Engineering Intern — Summer 2026",
            description=(
                "12-week paid internship. Work on developer tooling, CLI, and API. "
                "Mentorship from senior engineers. Stipend + equity."
            ),
            url="https://acme.example.com/jobs/intern-2026",
            content_hash=_content_hash("https://acme.example.com/jobs/intern-2026"),
            stack=["Python", "TypeScript", "React"],
            location="Remote",
            remote=True,
            posted_at=now - timedelta(days=12),
            source="ats",
            source_url="https://boards.greenhouse.io/acme",
            confidence="verified",
        ),
        Opportunity(
            company_id=beta.id,
            kind="oss_issue",
            title="Add TypeScript type inference for React hooks",
            description=(
                "The current type inference for `useQuery` doesn't handle generic "
                "type parameters correctly when used with React 19's new hooks. "
                "Good first issue — tests and types provided."
            ),
            url="https://github.com/beta/example/issues/42",
            content_hash=_content_hash("https://github.com/beta/example/issues/42"),
            stack=["TypeScript", "React"],
            location="Remote",
            remote=True,
            posted_at=now - timedelta(days=2),
            source="github",
            source_url="https://github.com/beta/example/issues/42",
            confidence="verified",
        ),
        Opportunity(
            company_id=None,
            kind="product_problem",
            title="No good local-first sync for SQLite on mobile",
            description=(
                "Looking for a lightweight sync engine that works with SQLite "
                "on iOS/Android and a Postgres backend. Must handle conflict "
                "resolution, offline-first, and schema migrations."
            ),
            url="https://news.ycombinator.com/item?id=99999999",
            content_hash=_content_hash("https://news.ycombinator.com/item?id=99999999"),
            stack=["SQLite", "Swift", "Kotlin", "Rust"],
            location="Remote",
            remote=True,
            posted_at=now - timedelta(days=1),
            source="hackernews",
            source_url="https://news.ycombinator.com/item?id=99999999",
            confidence="unverified",
        ),
    ]
    session.add_all(opps)
    session.flush()

    # Scores (manual — normally computed by rank())
    for opp in opps:
        score = Score(
            opportunity_id=opp.id,
            skill_match=45.0,
            hiring_signal=28.0,
            contribution_fit=18.0,
            total=91.0,
            band="Excellent",
            rationale="Strong stack overlap; recent posting; remote eligible",
        )
        session.add(score)

    # Outreach drafts
    outreach = Outreach(
        opportunity_id=opps[0].id,
        contact_id=contacts[0].id,
        subject="Founding Engineer role — Alex Chen",
        body=(
            "Hi Alex,\n\n"
            "I'm a full-stack engineer with 3 years building developer tools "
            "in Python/TypeScript. "
            "I saw your Founding Engineer posting and my background lines up: "
            "FastAPI, React, PostgreSQL. "
            "I've shipped a CLI tool used by 500+ devs and I'm looking for a "
            "small, fast-moving team.\n\n"
            "Would a 15-minute call this week work?\n\n"
            "Portfolio: https://github.com/varun-pahuja\n\n"
            "— Varun"
        ),
        status="draft",
    )
    session.add(outreach)

    # Tasks
    tasks = [
        Task(title="Draft outreach for Acme Founding Engineer", due_at=now + timedelta(days=1)),
        Task(title="Follow up on Beta Labs OSS issue", due_at=now + timedelta(days=3)),
        Task(title="Read Acme's engineering blog before call", due_at=now + timedelta(days=2)),
    ]
    session.add_all(tasks)

    # Proof of work
    pow_items = [
        ProofOfWork(
            opportunity_id=opps[0].id,
            kind="repo",
            url="https://github.com/varun-pahuja/dev-cli",
            summary="CLI tool for generating project scaffolding (Python, TypeScript). 500+ stars.",
        ),
        ProofOfWork(
            opportunity_id=opps[2].id,
            kind="pr",
            url="https://github.com/beta/example/pull/45",
            summary="Fixed TypeScript inference for useQuery generics. Merged.",
        ),
    ]
    session.add_all(pow_items)

    session.commit()
    print(f"Seeded: {len(opps)} opportunities, {len(contacts)} contacts, {len(tasks)} tasks")


if __name__ == "__main__":
    init_db()
    session = get_session()
    try:
        seed(session)
    finally:
        session.close()