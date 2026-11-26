"""The local dashboard: overview, editable sheet tabs, and detail pages."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import ActivityLog, Application, Company, Opportunity, Outreach, Score, Task
from .deps import get_db

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=str(HERE / "templates"))

TABS = ("opportunities", "outreach", "applications", "tasks", "activity")
STATUSES = ("new", "shortlisted", "contacted", "applied", "ignored")
TASK_STATUSES = ("open", "done")
OUTREACH_STATUSES = ("draft", "approved", "sent")
APPLICATION_STATUSES = ("todo", "applied", "interview", "offer", "rejected")

MAX_NOTES = 5000
MAX_SUBJECT = 300
MAX_BODY = 10_000
MAX_TITLE = 500
MAX_REQUEST_BYTES = 1_000_000
ROW_LIMIT = 500

DbSession = Annotated[Session, Depends(get_db)]


def _safe_url(value: str | None) -> str:
    """Only render http(s) links; blocks javascript:/data:/file: schemes."""
    if not value:
        return "#"
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    return "#"


templates.env.filters["safe_url"] = _safe_url


def _require_choice(value: str | None, allowed: tuple[str, ...], field: str) -> None:
    if value is not None and value not in allowed:
        raise HTTPException(status_code=422, detail=f"invalid {field}")


def _require_max(value: str | None, limit: int, field: str) -> None:
    if value is not None and len(value) > limit:
        raise HTTPException(status_code=422, detail=f"{field} too long (max {limit})")


def _opportunity_rows(db: Session) -> Sequence[Any]:
    return (
        db.query(Opportunity, Score, Company)
        .join(Score, Score.opportunity_id == Opportunity.id)
        .outerjoin(Company, Opportunity.company_id == Company.id)
        .order_by(Score.total.desc())
        .limit(ROW_LIMIT)
        .all()
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Startup Radar", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")

    @app.middleware("http")
    async def security_middleware(request: Request, call_next: Any) -> Response:
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_REQUEST_BYTES:
            return JSONResponse({"detail": "request too large"}, status_code=413)
        response: Response = await call_next(request)
        h = response.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "no-referrer"
        h["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        h["Cross-Origin-Resource-Policy"] = "same-origin"
        h["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'"
        )
        h["Cache-Control"] = "no-store"
        if request.url.scheme == "https":
            h["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

    @app.exception_handler(Exception)
    async def unhandled(_: Request, __: Exception) -> JSONResponse:
        # Never leak tracebacks or internals to the client.
        return JSONResponse({"detail": "internal error"}, status_code=500)

    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request, db: DbSession) -> HTMLResponse:
        total = db.query(func.count(Score.id)).scalar() or 0
        by_band = dict(db.query(Score.band, func.count(Score.id)).group_by(Score.band).all())
        by_kind = dict(
            db.query(Opportunity.kind, func.count(Opportunity.id))
            .group_by(Opportunity.kind)
            .all()
        )
        top = _opportunity_rows(db)[:5]
        tasks = (
            db.query(Task)
            .filter(Task.status == "open")
            .order_by(Task.created_at.desc())
            .limit(5)
            .all()
        )
        recent = db.query(ActivityLog).order_by(ActivityLog.ts.desc()).limit(8).all()
        return templates.TemplateResponse(
            request,
            "overview.html",
            {
                "total": total,
                "by_band": by_band,
                "by_kind": by_kind,
                "top": top,
                "tasks": tasks,
                "recent": recent,
            },
        )

    @app.get("/sheet/{tab}", response_class=HTMLResponse)
    def sheet(tab: str, request: Request, db: DbSession) -> Response:
        if tab not in TABS:
            return RedirectResponse("/sheet/opportunities", status_code=303)
        context: dict[str, object] = {"tab": tab, "tabs": TABS, "statuses": STATUSES}
        if tab == "opportunities":
            context["rows"] = _opportunity_rows(db)
        elif tab == "tasks":
            context["rows"] = db.query(Task).order_by(Task.created_at.desc()).all()
        elif tab == "outreach":
            from ..outreach import due, followup_count

            rows = (
                db.query(Outreach, Opportunity.title)
                .outerjoin(Opportunity, Outreach.opportunity_id == Opportunity.id)
                .order_by(Outreach.drafted_at.desc())
                .all()
            )
            context["rows"] = rows
            context["due_ids"] = {r.id for r in due(db)}
            context["followups"] = {r.id: followup_count(db, r.id) for r, _ in rows}
        elif tab == "applications":
            context["rows"] = db.query(Application).order_by(Application.id.desc()).all()
        else:
            context["rows"] = db.query(ActivityLog).order_by(ActivityLog.ts.desc()).limit(100).all()
        return templates.TemplateResponse(request, "sheet.html", context)

    @app.get("/opportunity/{opp_id}", response_class=HTMLResponse)
    def detail(opp_id: int, request: Request, db: DbSession) -> HTMLResponse:
        row = (
            db.query(Opportunity, Score, Company)
            .join(Score, Score.opportunity_id == Opportunity.id)
            .outerjoin(Company, Opportunity.company_id == Company.id)
            .filter(Opportunity.id == opp_id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Not found")
        opp, score, company = row
        drafts = (
            db.query(Outreach).filter(Outreach.opportunity_id == opp_id).all()
        )
        contacts = []
        if company is not None:
            from ..models import Contact

            contacts = db.query(Contact).filter(Contact.company_id == company.id).all()
        return templates.TemplateResponse(
            request,
            "detail.html",
            {
                "opp": opp,
                "score": score,
                "company": company,
                "drafts": drafts,
                "contacts": contacts,
            },
        )

    @app.patch("/api/opportunities/{opp_id}")
    def patch_opportunity(
        opp_id: int,
        db: DbSession,
        status: Annotated[str | None, Form()] = None,
        notes: Annotated[str | None, Form()] = None,
    ) -> Response:
        opp = db.get(Opportunity, opp_id)
        if opp is None:
            return Response(status_code=404)
        _require_choice(status, STATUSES, "status")
        _require_max(notes, MAX_NOTES, "notes")
        if status is not None:
            opp.status = status
        if notes is not None:
            opp.notes = notes
        db.commit()
        return Response(status_code=204)

    @app.post("/api/tasks")
    def add_task(title: Annotated[str, Form()], db: DbSession) -> RedirectResponse:
        _require_max(title, MAX_TITLE, "title")
        db.add(Task(title=title.strip()))
        db.commit()
        return RedirectResponse("/sheet/tasks", status_code=303)

    @app.patch("/api/tasks/{task_id}")
    def patch_task(
        task_id: int, status: Annotated[str, Form()], db: DbSession
    ) -> Response:
        _require_choice(status, TASK_STATUSES, "status")
        task = db.get(Task, task_id)
        if task is None:
            return Response(status_code=404)
        task.status = status
        db.commit()
        return Response(status_code=204)

    @app.delete("/api/tasks/{task_id}")
    def delete_task(task_id: int, db: DbSession) -> Response:
        task = db.get(Task, task_id)
        if task is not None:
            db.delete(task)
            db.commit()
        return Response(status_code=200)

    @app.patch("/api/outreach/{outreach_id}")
    def patch_outreach(
        outreach_id: int,
        db: DbSession,
        status: Annotated[str | None, Form()] = None,
        subject: Annotated[str | None, Form()] = None,
        body: Annotated[str | None, Form()] = None,
    ) -> Response:
        item = db.get(Outreach, outreach_id)
        if item is None:
            return Response(status_code=404)
        _require_choice(status, OUTREACH_STATUSES, "status")
        _require_max(subject, MAX_SUBJECT, "subject")
        _require_max(body, MAX_BODY, "body")
        if status is not None:
            item.status = status
            if status == "sent":
                from ..outreach import mark_sent

                mark_sent(item)
        if subject is not None:
            item.subject = subject
        if body is not None:
            item.body = body
        db.commit()
        return Response(status_code=204)

    @app.post("/api/outreach")
    def create_outreach(
        opportunity_id: Annotated[int, Form()], db: DbSession
    ) -> RedirectResponse:
        from ..outreach import draft

        if db.get(Opportunity, opportunity_id) is None:
            raise HTTPException(status_code=404, detail="Not found")
        draft(db, opportunity_id)
        return RedirectResponse("/sheet/outreach", status_code=303)

    @app.post("/api/outreach/{outreach_id}/followup")
    def followup_outreach(outreach_id: int, db: DbSession) -> Response:
        from ..outreach import record

        if record(db, outreach_id) is None:
            return Response(status_code=404)
        resp = Response(status_code=204)
        resp.headers["HX-Redirect"] = "/sheet/outreach"
        return resp

    @app.get("/api/outreach/{outreach_id}/eml")
    def download_eml(outreach_id: int, db: DbSession) -> Response:
        from ..models import Contact
        from ..outreach import render

        item = db.get(Outreach, outreach_id)
        if item is None:
            return Response(status_code=404)
        contact = db.get(Contact, item.contact_id) if item.contact_id else None
        filename = f"draft-{item.id}.eml"
        return Response(
            content=render(item, contact),
            media_type="message/rfc822",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.patch("/api/applications/{app_id}")
    def patch_application(
        app_id: int,
        db: DbSession,
        status: Annotated[str | None, Form()] = None,
        notes: Annotated[str | None, Form()] = None,
    ) -> Response:
        item = db.get(Application, app_id)
        if item is None:
            return Response(status_code=404)
        _require_choice(status, APPLICATION_STATUSES, "status")
        _require_max(notes, MAX_NOTES, "notes")
        if status is not None:
            item.status = status
        if notes is not None:
            item.notes = notes
        db.commit()
        return Response(status_code=204)

    return app
