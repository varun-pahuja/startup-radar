"""Notion export (Phase 6).

Creates/updates a Notion database with opportunities and companies.
Requires a Notion integration token (NOTION_TOKEN env var / Settings) and
a parent page ID where the database will be created/found.

Schema mirrors the Google Sheets tabs.
"""

from __future__ import annotations

import os
from typing import Any, cast

from notion_client import Client

from ..config import get_settings
from ..db import get_session, init_db
from ..models import Company, Opportunity, Score

NOTION_DATABASE_TITLE = "Startup Radar — Opportunities"
NOTION_COMPANIES_TITLE = "Startup Radar — Companies"


def _get_client() -> Client:
    settings = get_settings()
    token = settings.notion_token or os.getenv("NOTION_TOKEN", "")
    if not token:
        raise RuntimeError("NOTION_TOKEN not set")
    return Client(auth=token)


def _get_parent_page_id() -> str:
    settings = get_settings()
    page_id = settings.notion_parent_page_id or os.getenv("NOTION_PARENT_PAGE_ID", "")
    if not page_id:
        raise RuntimeError("NOTION_PARENT_PAGE_ID not set (parent page for databases)")
    return page_id


def _find_or_create_db(
    notion: Client, parent_id: str, title: str, properties: dict[str, Any]
) -> str:
    # Search existing databases under parent
    resp = cast(
        dict[str, Any],
        notion.search(
            query=title,
            filter={"property": "object", "value": "database"},
            page_size=10,
        ),
    )
    for db in resp.get("results", []):
        if db.get("title", [{}])[0].get("plain_text", "") == title:
            # Update properties if needed (add missing)
            existing_props = set(db.get("properties", {}).keys())
            new_props = {k: v for k, v in properties.items() if k not in existing_props}
            if new_props:
                notion.databases.update(
                    database_id=db["id"], properties={**db["properties"], **new_props}
                )
            return db["id"]
    # Create new
    db = cast(
        dict[str, Any],
        notion.databases.create(
            parent={"page_id": parent_id},
            title=[{"type": "text", "text": {"content": title}}],
            properties=properties,
        ),
    )
    return db["id"]


OPP_PROPERTIES: dict[str, Any] = {
    "Company": {"title": {}},
    "Title": {"rich_text": {}},
    "Kind": {
        "select": {
            "options": [
                {"name": k, "color": "default"}
                for k in ["job", "internship", "oss_issue", "product_problem"]
            ]
        }
    },
    "Score": {"number": {"format": "number"}},
    "Band": {
        "select": {
            "options": [
                {"name": b, "color": "default"}
                for b in ["Excellent", "High", "Medium", "Low"]
            ]
        }
    },
    "Source": {"rich_text": {}},
    "URL": {"url": {}},
    "Posted": {"date": {}},
    "Remote": {"checkbox": {}},
    "Stack": {"rich_text": {}},
}

COMP_PROPERTIES: dict[str, Any] = {
    "Name": {"title": {}},
    "Domain": {"rich_text": {}},
    "Location": {"rich_text": {}},
    "Remote": {"checkbox": {}},
    "URL": {"url": {}},
    "Confidence": {"rich_text": {}},
}


def _to_rich_text(value: str) -> list[dict]:
    return [{"type": "text", "text": {"content": str(value)}}] if value else []


def _to_number(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _to_date(value: str | None) -> dict | None:
    if not value:
        return None
    return {"start": value[:10]}


def _upsert_page(notion: Client, database_id: str, properties: dict[str, Any]) -> None:
    """Create or update a page by matching on the title property."""
    title_prop = next((k for k, v in properties.items() if v.get("title") is not None), None)
    if not title_prop:
        notion.pages.create(parent={"database_id": database_id}, properties=properties)
        return
    title_val = ""
    if "title" in properties[title_prop]:
        title_val = properties[title_prop]["title"][0]["text"]["content"]
    elif "rich_text" in properties[title_prop]:
        title_val = properties[title_prop]["rich_text"][0]["text"]["content"]
    # Query for existing
    query_method = getattr(notion.databases, "query", None)
    if query_method is None:
        raise RuntimeError("notion.databases.query not available")
    resp = cast(
        dict[str, Any],
        query_method(
            database_id=database_id,
            filter={"property": title_prop, "title": {"equals": title_val}},
            page_size=1,
        ),
    )
    if resp["results"]:
        page_id = resp["results"][0]["id"]
        notion.pages.update(page_id=page_id, properties=properties)
    else:
        notion.pages.create(parent={"database_id": database_id}, properties=properties)


def export_notion(parent_page_id: str | None = None) -> tuple[str, str]:
    """Export to Notion. Returns (opportunities_db_id, companies_db_id)."""
    init_db()
    session = get_session()
    try:
        notion = _get_client()
        parent = parent_page_id or _get_parent_page_id()

        opp_db = _find_or_create_db(notion, parent, NOTION_DATABASE_TITLE, OPP_PROPERTIES)
        comp_db = _find_or_create_db(notion, parent, NOTION_COMPANIES_TITLE, COMP_PROPERTIES)

        # Opportunities
        opp_rows = (
            session.query(Opportunity, Score, Company)
            .join(Score, Score.opportunity_id == Opportunity.id)
            .outerjoin(Company, Opportunity.company_id == Company.id)
            .order_by(Score.total.desc())
            .all()
        )
        for opp, score, company in opp_rows:
            props = {
                "Company": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": company.name if company else "Unknown"},
                        }
                    ]
                },
                "Title": {"rich_text": _to_rich_text(opp.title)},
                "Kind": {"select": {"name": opp.kind}},
                "Score": {"number": _to_number(round(score.total))},
                "Band": {"select": {"name": score.band}},
                "Source": {"rich_text": _to_rich_text(opp.source)},
                "URL": {"url": opp.url},
                "Posted": {
                    "date": _to_date(
                        opp.posted_at.strftime("%Y-%m-%d") if opp.posted_at else None
                    )
                },
                "Remote": {"checkbox": opp.remote},
                "Stack": {"rich_text": _to_rich_text(", ".join(opp.stack or []))},
            }
            _upsert_page(notion, opp_db, props)

        # Companies
        comp_rows = session.query(Company).order_by(Company.name).all()
        for c in comp_rows:
            props = {
                "Name": {"title": [{"type": "text", "text": {"content": c.name}}]},
                "Domain": {"rich_text": _to_rich_text(c.domain or "")},
                "Location": {"rich_text": _to_rich_text(c.location)},
                "Remote": {"checkbox": c.remote},
                "URL": {"url": c.url if c.url else None},
                "Confidence": {"rich_text": _to_rich_text(c.confidence)},
            }
            _upsert_page(notion, comp_db, props)

        return opp_db, comp_db
    finally:
        session.close()