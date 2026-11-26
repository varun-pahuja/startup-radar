# PLAN.md

Phased roadmap. Each phase ships something runnable and leaves a test behind.

| Phase | Ships | Done when |
|---|---|---|
| 0 | Packaging, config, models, DB, CLI, doctor, CI | `doctor` green, CI passes |
| 1 | GitHub + HN + heuristics → score → markdown/CSV | one command yields a real `top_opportunities.md` |
| 2 | FastAPI + dashboard overview + editable sheet tabs | edit a row in the browser, it persists |
| 3 | YC + ATS + RSS adapters | ≥3 sources merged, deduped |
| 4 | LLM enrichment (hybrid) + public contact discovery | works with LLM off; richer with it on |
| 5 | Outreach drafting + follow-up queue (draft-only) | drafts export to `.eml`; nothing sends |
| 6 | Optional exports: Sheets, Notion, static HTML | on-demand sync works |
| 7 | Cache + scheduling (cron / GH Action) → daily report | scheduled run writes report |
| 8 | OSS hardening: docs, templates, Docker, seed, release | a stranger installs and runs it |
| 9 (optional) | Next.js/AG-Grid upgrade, read API | only if HTMX limits |

Phases 0–5 are the personal daily-use MVP. 6–8 make it open-source-ready.

## Deferred on purpose

Alembic migrations (use `create_all` until schema stabilises, then add),
Postgres tuning, auth, multi-user, telemetry.
