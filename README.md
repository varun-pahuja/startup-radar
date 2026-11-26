# Startup Radar

Find startups, internships, and open-source issues worth your time — then prove
you're worth theirs.

Startup Radar is a local, config-driven research assistant for job seekers. It
pulls real opportunities from legal public sources, scores them against *your*
profile, and gives you a dashboard where you track, edit, and act on them.

It is **not** an auto-applier and it never sends anything for you. Every contact
and every claim carries its source; anything unverified is labelled as such.

## Honesty Rules (enforced in code)

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
# 1. Clone and enter
git clone https://github.com/varun-pahuja/startup-radar
cd startup-radar

# 2. Create virtual environment with Python 3.12
uv venv .venv --python 3.12
source .venv/bin/activate  # bash/zsh
# OR: source .venv/bin/activate.fish  # fish shell

# 3. Install dependencies
uv pip install -e ".[dev]"

# 4. Configure
cp .env.example .env
# Edit .env with your editor:
#   GITHUB_TOKEN=ghp_xxx                    # required for GitHub API (5000 req/hr)
#   LLM_BASE_URL=http://localhost:3001/v1   # your freellmapi endpoint
#   LLM_API_KEY=your-unified-key            # freellmapi unified key
#   LLM_MODEL=auto                          # or specific model like "gpt-4o-mini"

# Enable LLM enrichment
sed -i 's/enabled: false/enabled: true/' config/llm.yaml

# Copy and edit your profile
cp config/profile.example.yaml config/profile.yaml
# Edit config/profile.yaml with your details

# 5. Verify setup
startup-radar doctor
# All checks should show "ok" including "llm: configured"

# 6. Run the pipeline
startup-radar discover --limit 50     # pull opportunities
startup-radar enrich                   # LLM enrichment (optional)
startup-radar rank                     # score & rank
startup-radar report                   # generate markdown + CSV reports

# 7. View results
cat reports/top_opportunities.md
cat reports/next_actions.md
cat reports/daily_report.md

# 8. Launch dashboard
startup-radar serve
# Open http://127.0.0.1:8000
```

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Secrets (gitignored): `GITHUB_TOKEN`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` |
| `config/profile.yaml` | Your profile (gitignored): skills, experience, preferences |
| `config/sources.yaml` | Toggle sources and their options |
| `config/scoring.yaml` | Skill weights, eligibility rules, band thresholds |
| `config/schedule.yaml` | Cron expressions (docs only; used by GitHub Actions) |
| `config/llm.yaml` | LLM provider, model, cost caps, task toggles |

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
| `startup-radar outreach eml <id> [--out DIR]` | Export draft to `.eml` file |
| `startup-radar outreach followups` | List follow-ups that are due |
| `startup-radar outreach followup <id>` | Record a follow-up and schedule next |
| `startup-radar cache [--list] [--stats] [--clear]` | Manage on-disk HTTP cache |
| `startup-radar version` | Print version |

## Dashboard

Run `startup-radar serve` and open `http://127.0.0.1:8000`:

- **Overview** — stats, top opportunities, recent tasks, activity
- **Opportunities** — editable table (status, notes), click for detail
- **Outreach** — drafts with subject, status, follow-up tracking, `.eml` download
- **Applications** — track applications with status (todo/applied/interview/offer/rejected)
- **Tasks** — add/complete/delete tasks with HTMX
- **Activity** — audit log of all actions

On detail page: see score breakdown, provenance, contacts, draft outreach list, and "Draft outreach" button.

## Outreach Workflow (draft-only, nothing sends)

```bash
# Create draft for opportunity #1
startup-radar outreach draft 1

# List all drafts
startup-radar outreach list

# Export to .eml (open in your mail client)
startup-radar outreach eml 1

# Follow-ups
startup-radar outreach followups      # list due
startup-radar outreach followup 1     # record one, schedules next (max 2)

# In dashboard: set status=sent → follow-up button appears automatically
```

## Contact Discovery

```bash
startup-radar contacts --limit 20
# Scans company sites for mailto: links, stores with confidence=unverified
# No guessed emails, no PII harvesting
```

## Cache Management

```bash
startup-radar cache --stats   # count + size
startup-radar cache --list    # table of entries
startup-radar cache --clear   # wipe all
```

## Export

```bash
# Static HTML (no server needed)
startup-radar sync --html
startup-radar sync --html --html-dir ./my-export

# Google Sheets (optional, requires service account)
startup-radar sync --sheets [--sheets-id ID]

# Notion (optional, requires integration token)
startup-radar sync --notion [--notion-parent PAGE_ID]
```

## LLM Enrichment (hybrid: heuristics always + LLM optional)

| Layer | Runs | What it does |
|---|---|---|
| **Heuristics** | Always | Extracts tags, skills, location, remote from description |
| **LLM** | When enabled | Seniority, summary, visa/remote flags, outreach drafts |

**Your freellmapi config** (`config/llm.yaml`):
```yaml
enabled: true
provider: openai-compatible
model: "auto"           # freellmapi routes to best model
temperature: 0.2
max_tokens: 800
cost_caps:
  max_requests_per_run: 50
  max_tokens_per_run: 200000
  max_input_tokens_per_call: 8000
  max_output_tokens_per_call: 2000
tasks:
  enrich_opportunity: true
  summarize_company: true
  draft_outreach: true
```

**Required `.env`**:
```bash
LLM_BASE_URL=http://localhost:3001/v1
LLM_API_KEY=your-unified-key
LLM_MODEL=auto
LLM_ENABLED=true
```

## Scheduling (via GitHub Actions)

- **Daily** (08:00 Asia/Kolkata): discover → rank → report → optional sync
- **Weekly** (Sun 19:00): full pipeline + HTML snapshot + summary

Add repo secrets in GitHub: `GITHUB_TOKEN`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`

## Testing & Quality

```bash
# Run tests
.venv/bin/pytest -q

# Lint
.venv/bin/ruff check .

# Type check
.venv/bin/mypy src
```

## Seed Demo Data

```bash
rm -f data/startup_radar.db
.venv/bin/python scripts/seed.py
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

## Architecture

- **Core**: config, models, db, http, provenance, cli, doctor
- **Sources**: GitHub, HN Algolia, YC, ATS (Ashby/Greenhouse/Lever/Workable), RSS
- **Enrichment**: heuristics + LLM (litellm, cost caps) + contact discovery
- **Scoring**: skill_match/hiring_signal/contribution_fit + eligibility gate
- **Dashboard**: FastAPI + Jinja2 + HTMX, editable sheets, detail page
- **Security**: CSP, SSRF guard, allowlists, length caps, vendored HTMX
- **Outreach**: draft-only, .eml export, follow-up queue (max 2)
- **Exports**: Google Sheets, Notion, static HTML
- **Cache**: on-disk JSON with TTL, CLI management
- **Scheduling**: GitHub Actions daily/weekly

## License

MIT — see `LICENSE`.