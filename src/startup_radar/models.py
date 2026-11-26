"""SQLAlchemy models. Nine tables cover the twelve concepts in the brief."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .provenance import Confidence, utcnow


class Base(DeclarativeBase):
    pass


class ProvenanceMixin:
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    confidence: Mapped[str] = mapped_column(
        String(20), default=Confidence.UNVERIFIED.value
    )


class Company(Base, ProvenanceMixin):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    domain: Mapped[str | None] = mapped_column(String(300), unique=True, default=None)
    description: Mapped[str] = mapped_column(Text, default="")
    stage: Mapped[str] = mapped_column(String(50), default="")
    size: Mapped[str] = mapped_column(String(50), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    url: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    opportunities: Mapped[list[Opportunity]] = relationship(back_populates="company")


class Opportunity(Base, ProvenanceMixin):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), default=None)
    kind: Mapped[str] = mapped_column(String(30))  # job | internship | oss_issue | product_problem
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    stack: Mapped[list[str]] = mapped_column(JSON, default=list)
    location: Mapped[str] = mapped_column(String(200), default="")
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(50), default="")
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="new")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company: Mapped[Company | None] = relationship(back_populates="opportunities")
    score: Mapped[Score | None] = relationship(back_populates="opportunity", uselist=False)


class Contact(Base, ProvenanceMixin):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), default=None)
    name: Mapped[str] = mapped_column(String(200), default="Unknown")
    role: Mapped[str] = mapped_column(String(200), default="Unknown")
    email: Mapped[str] = mapped_column(String(300), default="Not Publicly Available")
    profile_url: Mapped[str] = mapped_column(String(1000), default="")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), unique=True)
    skill_match: Mapped[float] = mapped_column(Float, default=0.0)
    hiring_signal: Mapped[float] = mapped_column(Float, default=0.0)
    contribution_fit: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    band: Mapped[str] = mapped_column(String(20), default="Low")
    rationale: Mapped[str] = mapped_column(Text, default="")
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    opportunity: Mapped[Opportunity] = relationship(back_populates="score")


class Application(Base, ProvenanceMixin):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), default=None)
    type: Mapped[str] = mapped_column(String(20), default="application")  # application | referral
    status: Mapped[str] = mapped_column(String(30), default="todo")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    notes: Mapped[str] = mapped_column(Text, default="")


class Outreach(Base, ProvenanceMixin):
    __tablename__ = "outreach"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), default=None)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), default=None)
    channel: Mapped[str] = mapped_column(String(20), default="email")
    subject: Mapped[str] = mapped_column(String(300), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | approved | sent
    drafted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    followup_due: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class ProofOfWork(Base):
    __tablename__ = "proof_of_work"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), default=None)
    kind: Mapped[str] = mapped_column(String(20), default="repo")  # repo | demo | pr | writeup
    url: Mapped[str] = mapped_column(String(1000), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    due_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    status: Mapped[str] = mapped_column(String(20), default="open")
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    action: Mapped[str] = mapped_column(String(50))
    entity: Mapped[str] = mapped_column(String(50), default="")
    entity_id: Mapped[int | None] = mapped_column(Integer, default=None)
    note: Mapped[str] = mapped_column(Text, default="")
