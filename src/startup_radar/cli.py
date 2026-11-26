"""Command-line interface."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from . import __version__

app = typer.Typer(help="Startup Radar — find opportunities worth your time.", no_args_is_help=True)
console = Console()


@app.command()
def version() -> None:
    """Print the version."""
    console.print(f"startup-radar {__version__}")


@app.command()
def doctor() -> None:
    """Check environment, config, database, and credentials."""
    from .doctor import run_checks

    checks = run_checks()
    table = Table(title="startup-radar doctor")
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail")
    for c in checks:
        status = "[green]ok[/green]" if c.ok else "[red]fail[/red]"
        table.add_row(c.name, status, c.detail)
    console.print(table)
    if not all(c.ok for c in checks):
        raise typer.Exit(code=1)


@app.command()
def discover(
    limit: int = typer.Option(0, help="Cap total opportunities stored (0 = no cap)."),
    enrich: bool = typer.Option(False, help="Run LLM enrichment after discovery."),
) -> None:
    """Pull opportunities from enabled sources into the database."""
    from .pipeline import discover as run
    from .pipeline import enrich as run_enrich

    run(limit=limit or None)
    if enrich:
        run_enrich()


@app.command()
def enrich() -> None:
    """Run LLM enrichment on unscored opportunities (requires config/llm.yaml enabled)."""
    from .pipeline import enrich as run

    run()


@app.command()
def contacts(
    limit: int = typer.Option(200, help="Max companies to scan (0 = no cap)."),
) -> None:
    """Find contact emails a company publishes on its own site (never guessed)."""
    from .enrich.contacts import discover as run

    run(limit=limit or None)


outreach_app = typer.Typer(help="Draft-only outreach. Nothing is ever sent.", no_args_is_help=True)
app.add_typer(outreach_app, name="outreach")


@outreach_app.command("draft")
def outreach_draft(opportunity_id: int = typer.Argument(..., help="Opportunity id.")) -> None:
    """Create (or return) a draft for an opportunity."""
    from .db import get_session, init_db
    from .outreach import draft

    init_db()
    session = get_session()
    try:
        item = draft(session, opportunity_id)
    finally:
        session.close()
    if item is None:
        console.print(f"[red]no opportunity #{opportunity_id}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]draft #{item.id}[/green] {item.subject}")


@outreach_app.command("list")
def outreach_list() -> None:
    """Show drafts and follow-up state."""
    from .db import get_session, init_db
    from .models import Outreach
    from .outreach import followup_count

    init_db()
    session = get_session()
    try:
        rows = session.query(Outreach).order_by(Outreach.drafted_at.desc()).all()
        table = Table(title="outreach")
        table.add_column("id")
        table.add_column("status")
        table.add_column("subject")
        table.add_column("follow-up")
        for r in rows:
            due_at = r.followup_due.strftime("%b %d") if r.followup_due else "—"
            if r.followup_due:
                due_at += f" ({followup_count(session, r.id)}/2)"
            table.add_row(str(r.id), r.status, r.subject[:50], due_at)
        console.print(table)
    finally:
        session.close()


@outreach_app.command("eml")
def outreach_eml(
    outreach_id: int = typer.Argument(..., help="Outreach id."),
    out: str = typer.Option("", "--out", help="Output directory (default drafts/)."),
) -> None:
    """Write a draft to a .eml file you can open in your own mail client."""
    from pathlib import Path

    from .db import get_session, init_db
    from .models import Contact, Outreach
    from .outreach import export

    init_db()
    session = get_session()
    try:
        item = session.get(Outreach, outreach_id)
        if item is None:
            console.print(f"[red]no outreach #{outreach_id}[/red]")
            raise typer.Exit(code=1)
        contact = session.get(Contact, item.contact_id) if item.contact_id else None
        path = export(item, contact, Path(out) if out else None)
    finally:
        session.close()
    console.print(f"[green]wrote[/green] {path}")


@outreach_app.command("followups")
def outreach_followups() -> None:
    """List follow-ups that are due now."""
    from .db import get_session, init_db
    from .outreach import due

    init_db()
    session = get_session()
    try:
        rows = due(session)
    finally:
        session.close()
    if not rows:
        console.print("[yellow]no follow-ups due[/yellow]")
        return
    for r in rows:
        console.print(f"#{r.id}  {r.subject[:70]}")


@outreach_app.command("followup")
def outreach_followup(outreach_id: int = typer.Argument(..., help="Outreach id.")) -> None:
    """Record one follow-up and schedule the next (max two)."""
    from .db import get_session, init_db
    from .outreach import record

    init_db()
    session = get_session()
    try:
        item = record(session, outreach_id)
    finally:
        session.close()
    if item is None:
        console.print(f"[red]no outreach #{outreach_id}[/red]")
        raise typer.Exit(code=1)
    nxt = item.followup_due.strftime("%b %d") if item.followup_due else "queue closed"
    console.print(f"[green]follow-up recorded[/green]; next: {nxt}")


@app.command()
def rank() -> None:
    """Score unscored opportunities and assign bands."""
    from .pipeline import rank as run

    run()


@app.command()
def report() -> None:
    """Write markdown + CSV reports to reports/."""
    from .report import generate

    generate()


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind address."),
    port: int = typer.Option(8000, help="Port."),
) -> None:
    """Run the local dashboard."""
    import uvicorn

    from .db import init_db
    from .web.app import create_app

    init_db()
    uvicorn.run(create_app(), host=host, port=port, server_header=False)


@app.command()
def sync(
    sheets: bool = typer.Option(False, "--sheets", help="Export to Google Sheets."),
    notion: bool = typer.Option(False, "--notion", help="Export to Notion."),
    html: bool = typer.Option(False, "--html", help="Export static HTML snapshot."),
    sheets_id: str = typer.Option("", "--sheets-id", help="Existing spreadsheet ID (optional)."),
    notion_parent: str = typer.Option(
        "", "--notion-parent", help="Notion parent page ID (optional)."
    ),
    html_dir: str = typer.Option(
        "", "--html-dir", help="Output directory for HTML (default reports/html)."
    ),
) -> None:
    """Export data to external destinations (Phase 6)."""
    if not any([sheets, notion, html]):
        console.print("[yellow]Nothing to do. Use --sheets, --notion, or --html.[/yellow]")
        raise typer.Exit(code=1)

    if sheets:
        console.print("[cyan]Exporting to Google Sheets...[/cyan]")
        from .exporters import export_sheets

        try:
            sid = export_sheets(spreadsheet_id=sheets_id or None)
            console.print(f"[green]Sheets done[/green]: spreadsheet {sid}")
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Sheets failed:[/red] {exc}")

    if notion:
        console.print("[cyan]Exporting to Notion...[/cyan]")
        from .exporters import export_notion

        try:
            opp_db, comp_db = export_notion(parent_page_id=notion_parent or None)
            console.print(f"[green]Notion done[/green]: opps={opp_db}, companies={comp_db}")
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Notion failed:[/red] {exc}")

    if html:
        console.print("[cyan]Exporting static HTML...[/cyan]")
        from pathlib import Path

        from .exporters import export_html

        try:
            out = export_html(Path(html_dir) if html_dir else None)
            console.print(f"[green]HTML done[/green]: {out}")
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]HTML failed:[/red] {exc}")


@app.command()
def cache(
    list_entries: bool = typer.Option(False, "--list", "-l", help="List cached entries."),
    clear: bool = typer.Option(False, "--clear", help="Clear all cached entries."),
    stats: bool = typer.Option(False, "--stats", help="Show cache statistics."),
) -> None:
    """Manage the on-disk HTTP cache."""

    from .config import data_dir

    cache_dir = data_dir() / "cache"
    if not cache_dir.exists():
        console.print("[yellow]No cache directory found[/yellow]")
        return

    if clear:
        for f in cache_dir.glob("*.json"):
            f.unlink()
        console.print("[green]Cache cleared[/green]")
        return

    entries = list(cache_dir.glob("*.json"))
    if stats:
        total_size = sum(f.stat().st_size for f in entries)
        console.print(f"[cyan]Cache entries:[/cyan] {len(entries)}")
        console.print(f"[cyan]Total size:[/cyan] {total_size / 1024:.1f} KB")
        return

    if list_entries or not (stats or clear):
        table = Table(title="HTTP cache")
        table.add_column("key (sha256)")
        table.add_column("size")
        table.add_column("age")
        import time

        now = time.time()
        for f in sorted(entries, key=lambda p: p.stat().st_mtime, reverse=True):
            age_sec = now - f.stat().st_mtime
            if age_sec < 3600:
                age = f"{age_sec / 60:.0f}m"
            elif age_sec < 86400:
                age = f"{age_sec / 3600:.1f}h"
            else:
                age = f"{age_sec / 86400:.1f}d"
            table.add_row(f.stem[:16] + "...", f"{f.stat().st_size} B", age)
        console.print(table)


if __name__ == "__main__":
    app()
