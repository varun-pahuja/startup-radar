# Startup Radar

Find startups, internships, and open-source issues worth your time — then prove
you're worth theirs.

Startup Radar is a local, config-driven research assistant for job seekers. It
pulls real opportunities from legal public sources, scores them against *your*
profile, and gives you a dashboard where you track, edit, and act on them.

It is **not** an auto-applier and it never sends anything for you. Every contact
and every claim carries its source; anything unverified is labelled as such.

## Honesty rules (enforced in code)

- No fabricated startups, contacts, jobs, emails, applications, or totals.
- Unverified values are `Unknown`, `Unverified`, or `Not Publicly Available`.
- Every evidence row stores `source_url`, `fetched_at`, and `confidence`.
- Outreach is **draft-only** — nothing is ever sent automatically.
- Skills are split into `demonstrated` vs `learning`.

## Sources (allowlist)

GitHub API · Hacker News (Algolia) · YC OSS dataset · Ashby / Greenhouse / Lever
/ Workable public job boards · curated RSS. No scraping of sites whose terms
forbid it (LinkedIn, Wellfound, Internshala, Cutshort, …).

## Quickstart

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env            # add GITHUB_TOKEN (optional but recommended)
cp config/profile.example.yaml config/profile.yaml   # then edit it
startup-radar doctor
startup-radar discover
startup-radar rank
startup-radar report
startup-radar serve             # dashboard at http://127.0.0.1:8000
```

## Docker

```bash
docker build -t startup-radar .
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/reports:/app/reports \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/.env:/app/.env:ro \
  startup-radar
```

## Commands

| Command | What it does |
|---|---|
| `startup-radar doctor` | Check env, config, DB, token, source reachability |
| `startup-radar discover [--limit N] [--enrich]` | Pull opportunities from enabled sources |
| `startup-radar enrich` | Run LLM enrichment on unscored opportunities |
| `startup-radar rank` | Score unscored opportunities and assign bands |
| `startup-radar report` | Write `top_opportunities.md`, `next_actions.md`, `daily_report.md` + CSVs |
| `startup-radar serve [--host HOST] [--port PORT]` | Run the local dashboard |
| `startup-radar sync [--sheets] [--notion] [--html]` | Export to Google Sheets / Notion / static HTML |
| `startup-radar contacts [--limit N]` | Find published emails on company sites |
| `startup-radar outreach draft <id>` | Create (or return) a draft for an opportunity |
| `startup-radar outreach list` | Show drafts and follow-up state |
| `startup-radar outreach eml <id> [--out DIR]` | Export draft to .eml file |
| `startup-radar outreach followups` | List follow-ups that are due |
| `startup-radar outreach followup <id>` | Record a follow-up and schedule next |
| `startup-radar cache [--list] [--stats] [--clear]` | Manage on-disk HTTP cache |
| `startup-radar version` | Print version |

## Configuration

| File | Purpose |
|---|---|
| `config/profile.yaml` | Your profile (gitignored, seeded from public GitHub) |
| `config/sources.yaml` | Toggle sources and their options |
| `config/scoring.yaml` | Skill weights, eligibility rules, band thresholds |
| `config/schedule.yaml` | Cron expressions (docs only; used by GitHub Actions) |
| `config/llm.yaml` | LLM provider, model, cost caps, task toggles |

## Scheduling (via GitHub Actions)

- **Daily** (08:00 Asia/Kolkata): discover → rank → report → optional sync
- **Weekly** (Sun 19:00): full pipeline + HTML snapshot + summary

Set repo secrets to enable cloud sync:
- `GITHUB_TOKEN` (optional, raises rate limit)
- `GOOGLE_SERVICE_ACCOUNT_JSON` for Sheets
- `NOTION_TOKEN` + `NOTION_PARENT_PAGE_ID` for Notion

## Security

- Strict CSP, HSTS (on HTTPS), 1 MB body cap, generic error handler
- SSRF guard on all outbound HTTP; `http(s)`-only link filter in templates
- Input allowlists + length caps on all writes
- Vendored HTMX (no CDN); no server header
- CI: gitleaks, pip-audit, bandit; Dependabot

See `SECURITY.md`, `SECURITY_CHECKLIST.md`, `THREAT_MODEL.md`, `AI_SECURITY.md`,
`PRIVACY.md`, `INCIDENT_RESPONSE.md`, `ARCHITECTURE.md`, `docs/sources-policy.md`.

## License

MIT — see `LICENSE`.