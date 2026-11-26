"""Static HTML export (Phase 6).

Renders the dashboard data as standalone HTML files — no server needed.
Useful for sharing a snapshot or hosting on GitHub Pages / Netlify / S3.
"""

from __future__ import annotations

from pathlib import Path

from ..config import reports_dir
from ..db import get_session, init_db
from ..models import Company, Opportunity, Outreach, Score

HTML_TEMPLATE = (
    "<!doctype html>\n"
    '<html lang="en">\n'
    "<head>\n"
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    "<title>{title}</title>\n"
    "<style>\n"
    "  * {{ box-sizing: border-box; }}\n"
    "  body {{ font-family: system-ui, -apple-system, sans-serif; "
    "line-height: 1.5; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }}\n"
    "  h1, h2, h3 {{ margin-top: 2rem; }}\n"
    "  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}\n"
    "  th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; font-size: 0.9rem; }}\n"
    "  th {{ background: #f5f5f5; position: sticky; top: 0; }}\n"
    "  tr:nth-child(even) {{ background: #fafafa; }}\n"
    "  .band {{ padding: 0.2rem 0.5rem; border-radius: 0.3rem; "
    "font-weight: 600; font-size: 0.85rem; display: inline-block; }}\n"
    "  .excellent {{ background: #d4edda; color: #155724; }}\n"
    "  .high {{ background: #cce5ff; color: #004085; }}\n"
    "  .medium {{ background: #fff3cd; color: #856404; }}\n"
    "  .low {{ background: #f8d7da; color: #721c24; }}\n"
    "  a {{ color: #0066cc; text-decoration: none; }}\n"
    "  a:hover {{ text-decoration: underline; }}\n"
    "  .muted {{ color: #666; }}\n"
    "  .empty {{ text-align: center; padding: 2rem; color: #999; }}\n"
    "  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, "
    "minmax(280px, 1fr)); gap: 1rem; margin: 1rem 0; }}\n"
    "  .card {{ border: 1px solid #ddd; border-radius: 0.5rem; "
    "padding: 1rem; background: #fff; }}\n"
    "  .card h3 {{ margin-top: 0; }}\n"
    "</style>\n"
    "</head>\n"
    "<body>\n"
    "{content}\n"
    "</body>\n"
    "</html>"
)

OVERVIEW_TEMPLATE = (
    "<h1>Startup Radar — Overview</h1>\n"
    '<p class="muted">Exported {timestamp} · {total} scored opportunities</p>\n'
    "<h2>By Band</h2>\n"
    "<ul>\n"
    "{by_band}\n"
    "</ul>\n"
    "<h2>By Kind</h2>\n"
    "<ul>\n"
    "{by_kind}\n"
    "</ul>\n"
    "<h2>Top 5</h2>\n"
    '<div class="grid">\n'
    "{top_cards}\n"
    "</div>"
)

OPPORTUNITY_CARD = (
    '<div class="card">\n'
    '  <h3><a href="{url}" target="_blank">{title}</a></h3>\n'
    '  <p><strong>{company}</strong> · <span class="band {band}">{band}</span> · {score}</p>\n'
    '  <p>{kind} · {source} · {stack}</p>\n'
    "</div>"
)

OPPORTUNITIES_PAGE = (
    "<h1>All Opportunities ({count})</h1>\n"
    "<table>\n"
    "  <thead><tr><th>Score</th><th>Band</th><th>Company</th>"
    "<th>Title</th><th>Kind</th><th>Source</th><th>Posted</th>"
    "<th>Remote</th><th>Stack</th></tr></thead>\n"
    "  <tbody>\n"
    "{rows}\n"
    "  </tbody>\n"
    "</table>"
)

OPP_ROW = (
    "<tr>\n"
    "  <td>{score}</td>\n"
    '  <td><span class="band {band}">{band}</span></td>\n'
    "  <td>{company}</td>\n"
    '  <td><a href="{url}" target="_blank">{title}</a></td>\n'
    "  <td>{kind}</td>\n"
    "  <td>{source}</td>\n"
    "  <td>{posted}</td>\n"
    "  <td>{remote}</td>\n"
    "  <td>{stack}</td>\n"
    "</tr>"
)

COMPANIES_PAGE = (
    "<h1>Companies ({count})</h1>\n"
    "<table>\n"
    "  <thead><tr><th>Name</th><th>Domain</th><th>Location</th>"
    "<th>Remote</th><th>URL</th><th>Confidence</th></tr></thead>\n"
    "  <tbody>\n"
    "{rows}\n"
    "  </tbody>\n"
    "</table>"
)

COMP_ROW = (
    "<tr>\n"
    "  <td>{name}</td>\n"
    "  <td>{domain}</td>\n"
    "  <td>{location}</td>\n"
    "  <td>{remote}</td>\n"
    '  <td><a href="{url}" target="_blank">{url}</a></td>\n'
    "  <td>{confidence}</td>\n"
    "</tr>"
)

OUTREACH_PAGE = (
    "<h1>Outreach Drafts ({count})</h1>\n"
    "<table>\n"
    "  <thead><tr><th>Opportunity</th><th>Contact</th>"
    "<th>Subject</th><th>Status</th><th>Follow-up</th></tr></thead>\n"
    "  <tbody>\n"
    "{rows}\n"
    "  </tbody>\n"
    "</table>"
)

OUTREACH_ROW = (
    "<tr>\n"
    '  <td><a href="{opp_url}" target="_blank">{opp_title}</a></td>\n'
    "  <td>{contact}</td>\n"
    "  <td>{subject}</td>\n"
    "  <td>{status}</td>\n"
    "  <td>{followup}</td>\n"
    "</tr>"
)

TASKS_PAGE = (
    "<h1>Tasks ({count})</h1>\n"
    "<ul>\n"
    "{items}\n"
    "</ul>"
)


def _band_class(band: str) -> str:
    return band.lower()


def export_html(out_dir: Path | None = None) -> Path:
    """Write static HTML snapshot to out_dir (default: reports/html)."""
    init_db()
    session = get_session()
    try:
        target = out_dir or (reports_dir() / "html")
        target.mkdir(parents=True, exist_ok=True)

        # Fetch data
        opp_rows = (
            session.query(Opportunity, Score, Company)
            .join(Score, Score.opportunity_id == Opportunity.id)
            .outerjoin(Company, Opportunity.company_id == Company.id)
            .order_by(Score.total.desc())
            .all()
        )
        companies = session.query(Company).order_by(Company.name).all()
        outreach_rows = session.query(Outreach).order_by(Outreach.drafted_at.desc()).all()

        from datetime import UTC, datetime
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        # Overview
        total = len(opp_rows)
        by_band: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        for opp, score, _ in opp_rows:
            by_band[score.band] = by_band.get(score.band, 0) + 1
            by_kind[opp.kind] = by_kind.get(opp.kind, 0) + 1
        top5 = opp_rows[:5]

        by_band_html = "".join(
            f"<li>{band}: {count}</li>" for band, count in sorted(by_band.items())
        )
        by_kind_html = "".join(
            f"<li>{kind}: {count}</li>" for kind, count in sorted(by_kind.items())
        )
        top_cards = "".join(
            OPPORTUNITY_CARD.format(
                company=company.name if company else "Unknown",
                title=opp.title[:80],
                url=opp.url,
                band=_band_class(score.band),
                score=round(score.total),
                kind=opp.kind,
                source=opp.source,
                stack=", ".join(opp.stack or [])[:80],
            )
            for opp, score, company in top5
        )
        overview = HTML_TEMPLATE.format(
            title="Startup Radar — Overview",
            content=OVERVIEW_TEMPLATE.format(
                timestamp=timestamp,
                total=total,
                by_band=by_band_html,
                by_kind=by_kind_html,
                top_cards=top_cards,
            ),
        )
        (target / "index.html").write_text(overview)

        # Opportunities
        opp_rows_html = "".join(
            OPP_ROW.format(
                score=round(score.total),
                band=_band_class(score.band),
                company=company.name if company else "Unknown",
                title=opp.title,
                url=opp.url,
                kind=opp.kind,
                source=opp.source,
                posted=opp.posted_at.strftime("%Y-%m-%d") if opp.posted_at else "—",
                remote="Yes" if opp.remote else "No",
                stack=", ".join(opp.stack or []),
            )
            for opp, score, company in opp_rows
        )
        opp_page = HTML_TEMPLATE.format(
            title="Startup Radar — Opportunities",
            content=OPPORTUNITIES_PAGE.format(count=total, rows=opp_rows_html),
        )
        (target / "opportunities.html").write_text(opp_page)

        # Companies
        comp_rows_html = "".join(
            COMP_ROW.format(
                name=c.name,
                domain=c.domain or "—",
                location=c.location or "—",
                remote="Yes" if c.remote else "No",
                url=c.url or "—",
                confidence=c.confidence,
            )
            for c in companies
        )
        comp_page = HTML_TEMPLATE.format(
            title="Startup Radar — Companies",
            content=COMPANIES_PAGE.format(count=len(companies), rows=comp_rows_html),
        )
        (target / "companies.html").write_text(comp_page)

        # Outreach
        out_rows_html = "".join(
            OUTREACH_ROW.format(
                opp_url=opp.url,
                opp_title=opp.title,
                contact=f"#{o.contact_id}" if o.contact_id else "—",
                subject=o.subject,
                status=o.status,
                followup=o.followup_due.strftime("%Y-%m-%d") if o.followup_due else "—",
            )
            for o in outreach_rows
            if (opp := session.get(Opportunity, o.opportunity_id)) is not None  # type: ignore[assignment]
        )
        out_page = HTML_TEMPLATE.format(
            title="Startup Radar — Outreach",
            content=OUTREACH_PAGE.format(count=len(outreach_rows), rows=out_rows_html),
        )
        (target / "outreach.html").write_text(out_page)

        # Tasks
        tasks = (
            session.query(Outreach)
            .filter(Outreach.followup_due.is_not(None))
            .order_by(Outreach.followup_due)
            .all()
        )
        task_items = "".join(
            f"<li><a href='outreach.html#outreach-{t.id}'>{t.subject[:80]}</a> "
            f"— due {t.followup_due.strftime('%Y-%m-%d') if t.followup_due else '—'}</li>"
            for t in tasks
        )
        task_page = HTML_TEMPLATE.format(
            title="Startup Radar — Tasks",
            content=TASKS_PAGE.format(count=len(tasks), items=task_items),
        )
        (target / "tasks.html").write_text(task_page)

        return target
    finally:
        session.close()