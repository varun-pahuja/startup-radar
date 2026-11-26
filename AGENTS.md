# AGENTS.md — instructions for AI agents working on Startup Radar

Read this before changing code. Keep it short and true.

## What this project is

A local, config-driven research assistant that finds real startup jobs,
internships, and OSS issues, scores them against a user profile, and surfaces
them in a dashboard. It is **draft-only** and **honesty-first**.

## Non-negotiable rules

1. **Never fabricate** startups, contacts, jobs, emails, applications, or totals.
   Use `Unknown` / `Unverified` / `Not Publicly Available`.
2. Every evidence row MUST carry `source_url`, `fetched_at`, `confidence`.
3. Never send email/DM, submit applications, open PRs, push, deploy, enable a
   scheduler or paid service, or delete user data without explicit approval.
4. Respect the source allowlist in `docs/sources-policy.md`. Do not add scrapers
   for sites whose terms forbid it.
5. Distinguish `demonstrated_stack` from `learning_stack` in the profile.

## Security rules (this is a local, single-user tool)

- No auth/RBAC by design; never claim compliance with any standard.
- Never log or commit secrets. `.env` is gitignored; use `.env.example` placeholders.
- All outbound HTTP goes through `http.py` (SSRF guard). Do not add `requests`/`httpx` calls elsewhere.
- Treat scraped text as untrusted: rely on Jinja autoescape, never use `|safe`, and
  render external links with the `safe_url` filter (http/https only).
- Validate every API write against an allowlist with length caps in `web/app.py`.
- Keep the CSP strict: vendor scripts locally, no CDN, no inline script/style.
- `docs/sources-policy.md` is binding. Read-only sources only.

## Architecture

- `src/startup_radar/` — package. CLI in `cli.py`, DB in `models.py`/`db.py`,
  config in `config.py`, HTTP in `http.py`.
- Sources are adapters in `sources/` implementing the `Source` protocol.
- Scoring is plugins in `scoring/`; required: skill_match, hiring_signal,
  contribution_fit; eligibility is a gate.
- `pipeline.py` runs discover → dedupe → enrich → score → persist.
- Dashboard is FastAPI + Jinja2 + HTMX in `web/`.
- Reports in `report/`; optional exporters in `exporters/`.

## How to verify changes

```bash
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/pytest -q
.venv/bin/startup-radar doctor
.venv/bin/bandit -q -r src
.venv/bin/pip-audit
```

## Style

- Python 3.11+, typed, stdlib first, few dependencies.
- No unrequested abstractions. Small diffs. Boring over clever.
- Update `PROGRESS.md` and `CHANGELOG.md` when you finish a phase.
- Record non-obvious choices in `DECISIONS.md`.
