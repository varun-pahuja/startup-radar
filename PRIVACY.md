# Privacy

Startup Radar is designed to keep your data on your machine.

## What is stored, and where
- `data/startup_radar.db` — discovered opportunities, scores, tasks, outreach
  drafts, applications, and an activity log.
- `config/profile.yaml` — your skills, targets, and contact details.
- `reports/` and `data/exports/` — generated markdown/CSV.
- `data/cache/` — cached HTTP responses.

All of these are gitignored and never committed.

## Telemetry
None. The tool does not phone home, track usage, or send analytics.

## Network calls
Only read-only requests to sources you enable (GitHub API, Hacker News Algolia,
ATS JSON endpoints, RSS feeds). If you enable the LLM, selected text is sent to
the endpoint **you** configure.

## Secrets
Tokens and keys live in `.env`, which is gitignored. They are never written to
the database, reports, or logs.

## Deleting your data
- Everything: delete `data/`, `reports/`, and `config/profile.yaml`.
- Rotate any tokens you had placed in `.env` if the machine was shared.

## Third parties
Opportunity text belongs to its original source; links point back to the source
page. This tool stores excerpts for personal research only. Respect each site's
terms — see [`docs/sources-policy.md`](docs/sources-policy.md).
