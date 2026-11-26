"""The pipeline: discover → enrich → dedupe → persist, then rank."""

from __future__ import annotations

import hashlib
from collections import Counter

from rich.console import Console
from sqlalchemy.orm import Session

from .config import profile, scoring, sources
from .db import get_session, init_db
from .enrich import get_adapter, is_enabled
from .enrich.llm_enrich import enrich_opportunity
from .models import ActivityLog, Company, Opportunity, Score
from .scoring import compute
from .sources import RawOpportunity, all_sources

console = Console()


def _content_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _get_or_create_company(session: Session, raw: RawOpportunity) -> Company | None:
    if not raw.company_name:
        return None
    company: Company | None = None
    if raw.company_domain:
        company = session.query(Company).filter(Company.domain == raw.company_domain).first()
    if company is None:
        company = session.query(Company).filter(Company.name == raw.company_name).first()
    if company is not None:
        return company
    company = Company(
        name=raw.company_name,
        domain=raw.company_domain,
        url=raw.company_url,
        remote=raw.remote,
        source_url=raw.url,
        confidence=raw.confidence,
    )
    session.add(company)
    session.flush()
    return company


def _store(session: Session, raw: RawOpportunity) -> bool:
    content_hash = _content_hash(raw.url)
    exists = (
        session.query(Opportunity).filter(Opportunity.content_hash == content_hash).first()
    )
    if exists is not None:
        return False
    company = _get_or_create_company(session, raw)
    session.add(
        Opportunity(
            company_id=company.id if company else None,
            kind=raw.kind,
            title=raw.title[:500],
            description=raw.description[:4000],
            url=raw.url,
            stack=raw.stack,
            location=raw.location,
            remote=raw.remote,
            posted_at=raw.posted_at,
            payload=raw.payload,
            source=raw.source,
            content_hash=content_hash,
            source_url=raw.url,
            confidence=raw.confidence,
        )
    )
    return True


def enrich() -> int:
    """Enrich unscored opportunities with LLM when enabled."""
    if not is_enabled():
        console.print(
            "[yellow]LLM enrichment disabled (set enabled: true in config/llm.yaml)[/yellow]"
        )
        return 0
    adapter = get_adapter()
    if adapter is None:
        console.print("[red]LLM adapter unavailable (check litellm install + config)[/red]")
        return 0

    init_db()
    session = get_session()
    enriched = 0
    try:
        opportunities = (
            session.query(Opportunity)
            .filter(Opportunity.description != "")
            .filter(~Opportunity.score.has())
            .all()
        )
        for opp in opportunities:
            result = enrich_opportunity(
                adapter,
                opp.title,
                opp.description,
                opp.stack or [],
                opp.location or "",
                opp.remote,
            )
            if result:
                # merge skills (dedupe)
                merged = list(dict.fromkeys((opp.stack or []) + result.get("skills", [])))
                opp.stack = merged
                # could store seniority/summary in payload
                opp.payload = {**opp.payload, "llm_enrichment": result}
                enriched += 1
        if enriched:
            session.commit()
            console.print(f"[green]enrich done[/green]: {enriched} opportunities enriched")
        else:
            console.print("[yellow]enrich: no opportunities enriched[/yellow]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]enrich failed:[/red] {exc}")
    finally:
        session.close()
    return enriched


def discover(limit: int | None = None) -> Counter[str]:
    init_db()
    cfg = sources()
    session = get_session()
    counts: Counter[str] = Counter()
    try:
        for source in all_sources(cfg):
            added = dupes = 0
            try:
                for raw in source.fetch(cfg.get(source.name, {})):
                    if limit and sum(counts.values()) >= limit:
                        break
                    if _store(session, raw):
                        added += 1
                        counts[raw.kind] += 1
                    else:
                        dupes += 1
            except Exception as exc:  # noqa: BLE001 - one bad source shouldn't stop the run
                console.print(f"[red]{source.name} failed:[/red] {exc}")
                continue
            session.commit()
            console.print(f"[cyan]{source.name}[/cyan]: +{added} new, {dupes} dupes")
        session.add(ActivityLog(action="discover", note=str(dict(counts))))
        session.commit()
    finally:
        session.close()
    console.print(f"[green]discover done[/green]: {dict(counts) or 'nothing new'}")
    return counts


def rank() -> int:
    init_db()
    session = get_session()
    prof = profile()
    sc = scoring()
    try:
        opportunities = session.query(Opportunity).filter(~Opportunity.score.has()).all()
        for opp in opportunities:
            result = compute(opp, prof, sc)
            session.add(
                Score(
                    opportunity_id=opp.id,
                    skill_match=result.skill_match,
                    hiring_signal=result.hiring_signal,
                    contribution_fit=result.contribution_fit,
                    total=result.total,
                    band=result.band,
                    rationale=result.rationale,
                )
            )
        session.add(ActivityLog(action="rank", note=f"scored {len(opportunities)}"))
        session.commit()
    finally:
        session.close()
    console.print(f"[green]rank done[/green]: scored {len(opportunities)}")
    return len(opportunities)
