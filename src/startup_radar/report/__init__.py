"""Reports: markdown for humans, CSV for spreadsheets."""

from __future__ import annotations

import csv
from typing import Any

from sqlalchemy.orm import Session

from ..config import data_dir, reports_dir
from ..db import get_session, init_db
from ..models import Company, Opportunity, Score

Row = tuple[Opportunity, Score, Company | None]


def _rows(session: Session) -> list[Any]:
    return (
        session.query(Opportunity, Score, Company)
        .join(Score, Score.opportunity_id == Opportunity.id)
        .outerjoin(Company, Opportunity.company_id == Company.id)
        .order_by(Score.total.desc())
        .all()
    )


def _suggested_action(opp: Opportunity) -> str:
    if opp.kind == "oss_issue":
        return "Read the issue, comment a short plan, then open one small PR."
    if opp.kind == "internship":
        return "Find a public contact and draft a 70–150 word note with one project link."
    return "Confirm the posting is live, then draft a short personalized note."


def _company_name(company: Company | None, opp: Opportunity) -> str:
    if company and company.name:
        return company.name
    return "Unknown"


def _write_top(rows: list[Row]) -> None:
    lines = ["# Top opportunities", "", f"{len(rows)} scored. Showing the top 10.", ""]
    lines += [
        "| # | Score | Band | Company | Role / issue | Kind | Source |",
        "|---|---|---|---|---|---|---|",
    ]
    for index, (opp, score, company) in enumerate(rows[:10], start=1):
        title = opp.title.replace("|", "/")[:60]
        lines.append(
            f"| {index} | {score.total:.0f} | {score.band} | {_company_name(company, opp)} "
            f"| [{title}]({opp.url}) | {opp.kind} | {opp.source} |"
        )
    lines.append("")
    (reports_dir() / "top_opportunities.md").write_text("\n".join(lines))


def _write_next(rows: list[Row], followups: list[Any] | None = None) -> None:
    lines = ["# Next actions", ""]
    if followups:
        lines += ["## Due follow-ups (max two per contact)", ""]
        lines += [
            f"- [ ] #{f.id} {f.subject[:80]} "
            f"(sent {f.sent_at.strftime('%b %d') if f.sent_at else 'unknown'})"
            for f in followups
        ]
        lines.append("")
    lines += ["Do these three today, in order.", ""]
    for index, (opp, score, company) in enumerate(rows, start=1):
        lines += [
            f"## {index}. {opp.title[:80]}",
            f"- **Company:** {_company_name(company, opp)}",
            f"- **Score:** {score.total:.0f} ({score.band})",
            f"- **Why:** {score.rationale}",
            f"- **Action:** {_suggested_action(opp)}",
            f"- **Link:** {opp.url}",
            "",
        ]
    if not rows:
        lines.append("No scored opportunities yet. Run `startup-radar discover` then `rank`.")
    (reports_dir() / "next_actions.md").write_text("\n".join(lines))


def _write_daily(rows: list[Row]) -> None:
    bands: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for opp, score, _ in rows:
        bands[score.band] = bands.get(score.band, 0) + 1
        kinds[opp.kind] = kinds.get(opp.kind, 0) + 1
    lines = [
        "# Daily report",
        "",
        f"Total scored: {len(rows)}",
        "",
        "## By band",
        *[f"- {band}: {count}" for band, count in sorted(bands.items())],
        "",
        "## By kind",
        *[f"- {kind}: {count}" for kind, count in sorted(kinds.items())],
        "",
        "See `top_opportunities.md` and `next_actions.md`.",
    ]
    (reports_dir() / "daily_report.md").write_text("\n".join(lines))


def _write_csv(path: str, header: list[str], rows: list[list[Any]]) -> None:
    out = data_dir() / "exports"
    out.mkdir(parents=True, exist_ok=True)
    with (out / path).open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _write_csvs(session: Session, rows: list[Row]) -> None:
    header = ["company", "title", "kind", "score", "band", "source", "url", "posted_at"]
    _write_csv(
        "opportunities.csv",
        header,
        [
            [
                _company_name(company, opp),
                opp.title,
                opp.kind,
                score.total,
                score.band,
                opp.source,
                opp.url,
                opp.posted_at.isoformat() if opp.posted_at else "",
            ]
            for opp, score, company in rows
        ],
    )
    _write_csv(
        "internships.csv",
        header,
        [
            [
                _company_name(company, opp),
                opp.title,
                opp.kind,
                score.total,
                score.band,
                opp.source,
                opp.url,
                opp.posted_at.isoformat() if opp.posted_at else "",
            ]
            for opp, score, company in rows
            if opp.kind == "internship"
        ],
    )
    _write_csv(
        "contributions.csv",
        header,
        [
            [
                _company_name(company, opp),
                opp.title,
                opp.kind,
                score.total,
                score.band,
                opp.source,
                opp.url,
                opp.posted_at.isoformat() if opp.posted_at else "",
            ]
            for opp, score, company in rows
            if opp.kind == "oss_issue"
        ],
    )
    companies = session.query(Company).order_by(Company.name).all()
    _write_csv(
        "startups.csv",
        ["name", "domain", "location", "remote", "url", "confidence"],
        [
            [c.name, c.domain or "", c.location, c.remote, c.url, c.confidence]
            for c in companies
        ],
    )


def generate() -> int:
    init_db()
    session = get_session()
    try:
        rows = _rows(session)
        from ..outreach import due

        followups = due(session)
        _write_top(rows)
        _write_next(rows[:3], followups)
        _write_daily(rows)
        _write_csvs(session, rows)
    finally:
        session.close()
    from rich.console import Console

    Console().print(f"[green]report done[/green]: {len(rows)} opportunities → reports/")
    return len(rows)
