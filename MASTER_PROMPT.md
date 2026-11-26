# MASTER_PROMPT.md — canonical product spec

This is the working canonical spec for Startup Radar. It captures the original
vision plus the agreed tweaks. When in doubt, this file wins; changes go here
first, then into `DECISIONS.md`.

## Vision

An autonomous career-intelligence system for a student/early engineer: discover
startups and opportunities, research them, find ways to contribute (proof of
work), draft outreach, and track everything — without ever fabricating data or
acting without approval.

## User

Engineering student in India (Varun Pahuja, MITS Gwalior, IoT). TypeScript-first
full-stack with Python, C++, Supabase/Postgres, Cloudflare, AI integrations, IoT
and security exposure. Wants remote or Indian early-stage internships
(2–200 employees, prefer 5–50), ~2–3 hrs/day, free/open-source tooling only.

## Hard constraints

- Never fabricate data, contacts, sent emails, applications, referrals, totals.
- Use `Unknown` / `Unverified` / `Not Publicly Available`.
- Distinguish demonstrated vs learning skills.
- Approval required before: sending email/DM, submitting applications, requesting
  referrals, opening PRs, pushing, deploying, enabling scheduled/paid services,
  deleting user data, connecting external accounts.

## Scoring (0–100)

Required signals: skill_match /50, hiring_signal /30, contribution_fit /20.
Eligibility is a gate (remote-or-India, not senior-only) — fail ⇒ Low.
Opt-in plugins: contact_accessibility, startup_relevance, eligibility_detail,
learning_value.
Bands: 85+ Excellent · 70–84 High · 55–69 Medium · <55 Low.

## Data model (9 tables)

`companies` · `contacts` · `opportunities` (kind: job|internship|oss_issue|
product_problem) · `applications` (type: application|referral) · `outreach` ·
`proof_of_work` · `scores` · `tasks` · `activity_log`.
Every evidence row: `source_url`, `fetched_at`, `confidence`.

## Sources (allowlist)

GitHub API · HN Algolia · YC OSS dataset · Ashby/Greenhouse/Lever/Workable JSON
· curated RSS. Excluded: LinkedIn, Wellfound, Internshala, Cutshort (ToS).

## Deliverables

- CLI: `doctor`, `discover`, `rank`, `report`, `serve`, `sync`.
- Dashboard (FastAPI + Jinja2 + HTMX): overview + editable sheet tabs
  (Opportunities, Outreach, Applications, Tasks, Activity) + opportunity detail.
- Reports: `top_opportunities.md`, `next_actions.md`, `daily_report.md`, CSVs.
- Optional: Google Sheets / Notion export, static HTML.

## Schedule (Asia/Kolkata)

Daily discovery 08:00 · status sync 18:00 · weekly report Sun 19:00.
Follow-ups: first after 5–7 days, second after 7–10 days, max two.

## Outreach

70–150 words, personalized, no mass sending, no guessed emails, no tracking
pixels. Drafts only.

## Non-goals

Auto-send, auto-apply, scraping protected sites, paid infra, telemetry, storing
others' private data.

## Tweaks vs the original brief

Adapters over agents · LLM optional (heuristics default) · provenance enforced
in schema · legal source allowlist · draft-only outreach · exporters as plugins
· scheduling via cron/Actions · SQLite default · 3 required signals + 4 opt-in ·
static/HTMX dashboard first · `profile.example.yaml` committed, real profile
gitignored.
