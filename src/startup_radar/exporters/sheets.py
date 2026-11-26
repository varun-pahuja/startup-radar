"""Google Sheets export (Phase 6).

Requires a service account with the Sheets API enabled. The service account
JSON is provided via GOOGLE_SERVICE_ACCOUNT_JSON env var (or Settings).
The spreadsheet ID can be passed or created on first run.
"""

from __future__ import annotations

import json
import os
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from ..config import get_settings
from ..db import get_session, init_db
from ..models import Company, Opportunity, Score

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_credentials() -> Credentials:
    settings = get_settings()
    raw = settings.google_service_account_json or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set")
    info = json.loads(raw)
    return Credentials.from_service_account_info(info, scopes=SCOPES)


def _get_or_create_spreadsheet(svc: Any, title: str = "Startup Radar") -> str:
    # Try to find existing spreadsheet by title
    drive = build("drive", "v3", credentials=svc._credentials)
    q = f"name='{title}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    resp = drive.files().list(q=q, fields="files(id)").execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]
    # Create new
    sheet = svc.spreadsheets().create(body={"properties": {"title": title}}).execute()
    return sheet["spreadsheetId"]


def _write_tab(
    svc: Any,
    spreadsheet_id: str,
    tab_name: str,
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    # Ensure tab exists
    meta = svc.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta.get("sheets", [])}
    if tab_name not in sheets:
        req = {"requests": [{"addSheet": {"properties": {"title": tab_name}}}]}
        svc.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=req).execute()
    # Clear and write
    range_name = f"'{tab_name}'"
    svc.spreadsheets().values().clear(spreadsheetId=spreadsheet_id, range=range_name).execute()
    body = {"values": [headers] + rows}
    svc.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()


def export_sheets(spreadsheet_id: str | None = None, title: str = "Startup Radar") -> str:
    """Export scored opportunities, companies, and outreach to Google Sheets.

    Returns the spreadsheet ID.
    """
    init_db()
    session = get_session()
    try:
        creds = _get_credentials()
        svc = build("sheets", "v4", credentials=creds)
        sid = spreadsheet_id or _get_or_create_spreadsheet(svc, title)

        # Opportunities
        opp_rows = (
            session.query(Opportunity, Score, Company)
            .join(Score, Score.opportunity_id == Opportunity.id)
            .outerjoin(Company, Opportunity.company_id == Company.id)
            .order_by(Score.total.desc())
            .all()
        )
        _write_tab(
            svc,
            sid,
            "Opportunities",
            [
                "Company",
                "Title",
                "Kind",
                "Score",
                "Band",
                "Source",
                "URL",
                "Posted",
                "Remote",
                "Stack",
            ],
            [
                [
                    company.name if company else "Unknown",
                    opp.title,
                    opp.kind,
                    round(score.total),
                    score.band,
                    opp.source,
                    opp.url,
                    opp.posted_at.strftime("%Y-%m-%d") if opp.posted_at else "",
                    "Yes" if opp.remote else "No",
                    ", ".join(opp.stack or []),
                ]
                for opp, score, company in opp_rows
            ],
        )

        # Companies
        comp_rows = session.query(Company).order_by(Company.name).all()
        _write_tab(
            svc,
            sid,
            "Companies",
            ["Name", "Domain", "Location", "Remote", "URL", "Confidence"],
            [
                [
                    c.name,
                    c.domain or "",
                    c.location,
                    "Yes" if c.remote else "No",
                    c.url,
                    c.confidence,
                ]
                for c in comp_rows
            ],
        )

        return sid
    finally:
        session.close()