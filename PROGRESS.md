# PROGRESS.md

## 2026-11-26 — Phases 0–2 complete, security baseline landed

### Phase 0 — Foundation (done)
- Repo initialised (git, MIT, pyproject, .gitignore, .env.example, CI, pre-commit).
- Docs: README, AGENTS, MASTER_PROMPT, PLAN, PROGRESS, DECISIONS, TASKS, CHANGELOG.
- Config: profile (seeded + example), sources, scoring, schedule, llm.
- Core: config, models, db, http, provenance, cli, doctor.
- `doctor` green; ruff/mypy/pytest clean.

### Phase 1 — First vertical slice (done)
- Source protocol + registry; GitHub and HN Algolia adapters.
- Heuristic enrichment; scoring (skill_match, hiring_signal, contribution_fit +
  eligibility gate); pipeline (discover/rank); markdown + CSV reports.
- Live run: 237 scored (15 OSS issues, 221 jobs, 1 internship).
- Unit tests for heuristics and scoring.

### Phase 2 — Dashboard (done)
- FastAPI app: overview, editable sheet tabs (opportunities, outreach,
  applications, tasks, activity), opportunity detail, allowlist-validated CRUD.
- HTMX vendored locally; custom CSS; `serve` initialises the DB and hides the
  server banner.
- Verified: `serve` returns 200 for pages and static assets; security headers
  present.
- Integration tests: pages, CRUD, validation.

### Security baseline (done — see SECURITY_CHECKLIST.md)
- Security headers + strict CSP + HSTS-on-HTTPS; 1 MB body cap; generic error
  handler.
- SSRF guard in `http.py`; `http(s)`-only link filter in templates.
- Input allowlists + length caps on all writes.
- CI: gitleaks + pip-audit + bandit; Dependabot. `bandit` clean, `pip-audit`
  reports no known vulnerabilities.
- Security regression tests added.
- Docs: SECURITY, THREAT_MODEL, AI_SECURITY, PRIVACY, INCIDENT_RESPONSE,
  ARCHITECTURE, docs/sources-policy.

### Next
- Phase 3: YC + ATS + RSS adapters.

## 2026-11-26 — Phase 3 complete (YC, ATS, RSS)

### Phase 3 — More sources (done)
- YC adapter: `https://api.ycombinator.com/v0.1/companies`, per-batch pagination
  (one request per batch), +200 opportunities verified.
- ATS adapters: Ashby, Greenhouse, Lever, Workable JSON endpoints.
- RSS adapter: feedparser, reuses HN HTML stripper; enabled via config.
- All registered in `sources/__init__.py`; `feedparser>=6` added.
- Verified: `discover` → `yc: +200`, `rank` → 200, `report` → 437 total.
- ruff/mypy/pytest green.

## 2026-11-26 — Phase 4 complete (LLM + contact discovery)

### Phase 4 — LLM enrichment + public contact discovery (done)
- LLM adapter (`src/startup_radar/enrich/llm.py`): `litellm` for any OpenAI-compatible
  endpoint (Groq, Google AI Studio, OpenRouter, Ollama, LM Studio, etc.).
- Cost caps (configurable in `config/llm.yaml`): 50 req/run, 200k tokens/run,
  8k input/2k output per call. Exceeding → `LLMCostExceeded`, falls back to
  heuristics-only.
- Enrichment tasks (`src/startup_radar/enrich/llm_enrich.py`):
  `enrich_opportunity` (skills, seniority, summary, remote/visa flags),
  `draft_outreach` (70-150 word cold email), `summarize_company` (2-3 sentences).
- Pipeline `enrich()` + `discover --enrich` flag; heuristics always run.
- Public contact discovery (`src/startup_radar/enrich/contacts.py`): extracts
  `mailto:` and plain emails from company homepage + `/contact` + `/careers` +
  `/jobs`. No guessed emails, no PII harvesting. Every row: source_url,
  fetched_at, confidence=unverified.
- Config: `config/llm.yaml` now includes `cost_caps` section.

## 2026-11-26 — Phase 5 complete (outreach + follow-ups)

### Phase 5 — Outreach drafting + follow-up queue (draft-only, done)
- Draft outreach (`src/startup_radar/outreach/draft.py`): template-based (70-150
  words, one clear ask, no fluff) + optional LLM via `draft_outreach`. Dedupe:
  one draft per opportunity (returns existing).
- `.eml` export (`src/startup_radar/outreach/eml.py`): RFC-5322 via stdlib
  `email.message.EmailMessage`. To header only when a published address exists;
  `X-Startup-Radar: draft-only` header. Nothing sends.
- Follow-up queue (`src/startup_radar/outreach/followup.py`): first nudge 5-7d
  (6d), second 7-10d (8d), max two. `mark_sent` on status=sent → sets
  `sent_at` + `followup_due`. `record()` logs ActivityLog, schedules next or
  clears queue.
- Reports: `next_actions.md` now lists due follow-ups at top.
- CLI sub-app: `outreach draft <id>`, `outreach list`, `outreach eml <id>`,
  `outreach followups`, `outreach followup <id>`.
- Web: detail page shows contacts + drafts list + "Draft outreach" button;
  outreach sheet shows opportunity title, follow-up due/count, follow-up button
  (HTMX), .eml download.

## 2026-11-26 — Phase 6 complete (optional exports)

### Phase 6 — Optional exports (done)
- Google Sheets export (`src/startup_radar/exporters/sheets.py`): service account
  auth; creates/updates spreadsheet with Opportunities + Companies tabs.
- Notion export (`src/startup_radar/exporters/notion.py`): integration token +
  parent page; creates/updates Opportunities + Companies databases with upsert.
- Static HTML export (`src/startup_radar/exporters/html.py`): standalone HTML
  snapshot (index, opportunities, companies, outreach, tasks) — no server needed.
- CLI: `sync --sheets --notion --html` with optional spreadsheet ID, parent page,
  output dir.
- Optional deps: `google-api-python-client`, `google-auth`, `notion-client`.

## 2026-11-26 — Phase 7 complete (cache + scheduling)

### Phase 7 — Cache + scheduling (done)
- On-disk JSON cache with TTL in `http.py` (used by all sources, 1h default).
- Cache CLI: `startup-radar cache --list` (table with key/size/age),
  `--stats` (count + total size), `--clear` (wipes all).
- GitHub Actions:
  - `.github/workflows/daily-discovery.yml`: scheduled 08:00 Asia/Kolkata,
    runs discover → rank → report → optional sync; passes DB as artifact.
  - `.github/workflows/weekly-report.yml`: scheduled Sun 19:00 Asia/Kolkata,
    full pipeline + HTML snapshot; posts summary to workflow run.
- Schedule documented in `config/schedule.yaml` (cron for daily/weekly, follow-up windows).
