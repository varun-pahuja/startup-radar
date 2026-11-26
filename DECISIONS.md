# DECISIONS.md — non-obvious choices

## D001 — SQLite + SQLAlchemy 2.0, `create_all` before Alembic
Zero-setup for a solo user; SQLAlchemy keeps Postgres a config change away.
Alembic deferred until the schema stabilises (Phase 8).

## D002 — Adapters, not runtime "agents"
The brief's 7 agents become source adapters + scorer plugins + an optional
enricher. Pure functions are testable and contributors can add a source without
touching the pipeline.

## D003 — LLM optional, heuristics always
Core runs with no API key and no cost. `litellm` (OpenAI-compatible) is opt-in
via `LLM_ENABLED`, so forks and offline users still work.

## D004 — Provenance in the schema
`source_url`, `fetched_at`, `confidence` are required columns on evidence
tables. "Never fabricate" becomes a constraint, not a promise.

## D005 — Legal source allowlist only
Only public APIs/feeds/ATS JSON. No LinkedIn/Wellfound/Internshala scraping —
their terms forbid it and an OSS project cannot ship that.

## D006 — Draft-only outreach
The tool never sends. It produces drafts and `.eml` exports; a human sends.

## D007 — Dashboard before cloud sheets
The editable grid lives in the app (FastAPI + HTMX). Google Sheets/Notion become
optional exporters in Phase 6 rather than the primary editing surface.

## D008 — Personal profile is gitignored
`config/profile.example.yaml` is committed; `config/profile.yaml` (real data) is
gitignored so the repo stays clean for open-sourcing.

## D009 — Python 3.12 via uv
System Python 3.14 lacks reliable wheels for the stack; uv provisions 3.12.14.
