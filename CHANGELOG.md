# CHANGELOG

All notable changes to this project. Format: Keep a Changelog; semver.

## [Unreleased]

### Added
- Project scaffold: MIT license, pyproject, config schema, docs.
- Core package: config, models, db, http, provenance, cli, doctor.
- Sources: GitHub (good-first-issues) and Hacker News (Who is hiring) adapters.
- Heuristic enrichment, scoring engine (skill/hiring/contribution + eligibility
  gate), discover/rank pipeline, markdown + CSV reports.
- Dashboard: overview, editable sheet tabs, detail page, CRUD APIs (FastAPI +
  Jinja2 + HTMX), vendored HTMX and custom CSS.
- Security: headers/CSP middleware, 1 MB body cap, generic error handler, SSRF
  guard, `http(s)`-only link filter, write allowlists + length caps.
- Security CI: gitleaks, pip-audit, bandit; Dependabot.
- Security docs: SECURITY, SECURITY_CHECKLIST, THREAT_MODEL, AI_SECURITY,
  PRIVACY, INCIDENT_RESPONSE, ARCHITECTURE, docs/sources-policy.
- Integration tests for pages, CRUD, validation, and security regressions.

### Changed
- Content dedupe and HTTP cache keys now use SHA-256 (was SHA-1).

### Fixed
- Hacker News parsing (official thread, candidate filtering, region gating).
- Region-restricted eligibility handling in scoring.

## [Unreleased]

### Added
- YC, ATS (Ashby/Greenhouse/Lever/Workable), and RSS source adapters.
- LLM enrichment adapter (`litellm`) with per-run cost caps (requests/tokens).
- LLM enrichment tasks: opportunity skills/summary, outreach drafts, company summaries.
- Public contact discovery from company websites (mailto: extraction only).
- Draft-only outreach: template + optional LLM drafts, deduped per opportunity.
- RFC-5322 `.eml` export (stdlib email, `X-Startup-Radar: draft-only` header).
- Follow-up queue: first 5-7d, second 7-10d, max two; recorded via ActivityLog.
- `next_actions.md` now surfaces due follow-ups.
- CLI: `contacts`, `outreach draft/list/eml/followups/followup` sub-commands.
- Dashboard: detail page contacts + drafts, outreach sheet with follow-up column + .eml download.

### Changed
- `config/llm.yaml` adds `cost_caps` section and task toggles.
- Outreach table: opportunity title link, follow-up due/count, HX-Redirect on mutations.

### Fixed
- Contact discovery skips platform hosts (github.com, linkedin.com) and filters placeholder domains (yourcompany.com, etc.).

## [Unreleased]

### Added
- Google Sheets export (service account, create/update spreadsheet, Opportunities + Companies tabs).
- Notion export (integration token + parent page, Opportunities + Companies databases with upsert).
- Static HTML export (standalone snapshot: index, opportunities, companies, outreach, tasks).
- CLI `sync` command with `--sheets`, `--notion`, `--html` flags and optional IDs/dir.
- Optional deps: `google-api-python-client`, `google-auth`, `notion-client`.

## [Unreleased]

### Added
- On-disk JSON cache with TTL in `http.py` (1h default, used by all sources).
- Cache management CLI: `cache --list/--stats/--clear`.
- GitHub Actions workflow: `daily-discovery.yml` (08:00 Asia/Kolkata, discover→rank→report→sync).
- GitHub Actions workflow: `weekly-report.yml` (Sun 19:00, full pipeline + HTML snapshot + summary).
- Schedule config: `config/schedule.yaml` with cron expressions and follow-up windows.
