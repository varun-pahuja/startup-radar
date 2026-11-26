# TASKS.md

Mirror of the active todo list, by phase. Check items off as they land.

## Phase 0 — Foundation
- [x] git init, .gitignore, MIT LICENSE, pyproject.toml
- [x] scaffold dirs
- [x] config YAMLs (profile seeded, sources, scoring, schedule, llm)
- [x] models + DTOs (9 tables, provenance)
- [x] db.py (create_all)
- [x] config.py + http.py + provenance.py
- [x] CLI skeleton + doctor.py
- [x] CI + pre-commit + ruff/mypy/pytest config
- [x] project docs

## Phase 1 — First vertical slice
- [x] Source protocol + registry
- [x] GitHub adapter
- [x] HN Algolia adapter
- [x] heuristics enrichment
- [x] scoring (skill_match, hiring_signal, contribution_fit, eligibility)
- [x] pipeline
- [x] markdown + CSV reports
- [x] tests

## Phase 2 — Dashboard
- [x] FastAPI app + overview
- [x] editable sheet tabs + CRUD
- [x] opportunity detail
- [x] serve command + styling
- [x] API tests

## Security baseline
- [x] headers + CSP + body cap + generic errors
- [x] SSRF guard + safe link filter
- [x] input allowlists + length caps
- [x] vendored HTMX (no CDN)
- [x] CI secret/dependency/SAST scans + Dependabot
- [x] security regression tests
- [x] security docs + triage (SECURITY_CHECKLIST.md)
- [ ] pin GitHub Actions to commit SHAs
- [ ] SBOM generation

## Phase 3 — More sources
- [x] YC adapter
- [x] ATS adapters (Ashby/Greenhouse/Lever/Workable)
- [x] RSS adapter

## Phase 4 — LLM enrichment + public contact discovery
- [x] LLM adapter (litellm, OpenAI-compatible) + cost caps
- [x] LLM enrichment tasks: enrich_opportunity, draft_outreach, summarize_company
- [x] Pipeline enrich() + discover --enrich
- [x] Public contact discovery (mailto: extraction from company site)
- [x] Contact model + verification (confidence=unverified, source_url)

## Phase 5 — Outreach drafting + follow-up queue (draft-only)
- [x] Draft outreach: template + optional LLM (draft_outreach)
- [x] Dedupe: one draft per opportunity
- [x] .eml export (RFC-5322 via stdlib email.message)
- [x] Follow-up queue: first 5-7d, second 7-10d, max 2
- [x] mark_sent on status=sent, record follow-up, HX-Redirect
- [x] next_actions.md includes due follow-ups
- [x] CLI: outreach draft/list/eml/followups/followup
- [x] Web: detail draft button + list, sheet shows opp title + follow-up + .eml

## Phase 6 — Optional exports
- [x] Google Sheets export (service account, create/update spreadsheet, Opportunities + Companies tabs)
- [x] Notion export (integration token, parent page, Opportunities + Companies databases)
- [x] Static HTML export (standalone HTML snapshot: index, opportunities, companies, outreach, tasks)
- [x] CLI sync command with --sheets, --notion, --html flags
- [x] Optional dependencies: google-api-python-client, google-auth, notion-client

## Phase 7 — Cache + scheduling
- [x] On-disk JSON cache with TTL (http.py) — used by all sources
- [x] Cache CLI: `cache --list/--stats/--clear`
- [x] GitHub Actions: daily-discovery.yml (discover → rank → report → sync)
- [x] GitHub Actions: weekly-report.yml (full pipeline + HTML snapshot)
- [x] Schedule documented in config/schedule.yaml (cron expressions for Asia/Kolkata)

## Phase 8–9
See PLAN.md.