# Architecture

## Overview
Startup Radar is a Python package with a CLI and a local FastAPI dashboard. It
discovers opportunities from read-only public sources, stores them in SQLite with
provenance, scores them against a YAML profile, and renders editable sheets.

```
config/*.yaml ──┐
                ▼
        ┌───────────────┐     ┌──────────────┐     ┌───────────────┐
        │   sources/    │────▶│  pipeline.py │────▶│    models.py  │
        │ github, hn,   │     │ discover/rank│     │   (SQLite)    │
        │ yc, ats, rss  │     └──────────────┘     └───────┬───────┘
        └───────────────┘            │                    │
                                     ▼                    ▼
                              scoring/engine.py      report/ + web/
                              enrich/heuristics.py   (markdown, CSV, HTML)
```

## Components
- `config.py` — resolves project home, env settings (`.env`), and YAML config.
- `http.py` — shared `httpx` client with disk cache and the **SSRF guard**
  (`ensure_safe_url`).
- `sources/` — adapters implementing the `Source` protocol, returning
  `RawOpportunity`. Only read-only GETs.
- `pipeline.py` — `discover()` (fetch → dedupe by SHA-256 of URL → persist) and
  `rank()` (score unscored rows).
- `enrich/heuristics.py` — deterministic tag/skill extraction (always on).
- `scoring/engine.py` — 3 signals + eligibility gate, produces a `Score`.
- `report/` — markdown + CSV into `reports/` and `data/exports/`.
- `web/app.py` — FastAPI app: overview, editable sheet tabs, detail, and
  allowlist-validated write APIs. Security middleware adds headers and a body
  cap; a generic handler hides tracebacks.
- `models.py` / `db.py` — nine SQLAlchemy tables with a provenance mixin;
  `create_all` for now (Alembic deferred).

## Data flow and trust boundaries
1. **Remote → parser** (untrusted): all fetched text is data.
2. **Parser → DB**: values length-capped; provenance stored per row.
3. **DB → HTML**: Jinja autoescape; URLs forced to `http(s)`; strict CSP.
4. **Browser → API**: same-origin; every writable field allowlist-validated.
5. **Config → outbound HTTP**: SSRF guard rejects non-HTTP and private hosts.

## Design constraints
- Draft-only: no sending, applying, pushing, or deploying.
- Honesty-first: every evidence row carries `source_url`, `fetched_at`,
  `confidence`; missing data is `Unknown` / `Not Publicly Available`.
- Local-first: SQLite + localhost; no auth, no multi-tenancy by design.

## Key decisions
See `DECISIONS.md` (license, stack, storage, source allowlist, LLM toggles).
