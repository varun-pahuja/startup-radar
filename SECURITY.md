# Security policy

## What this is
Startup Radar is a **local, single-user** tool. It binds to `127.0.0.1` by
default and has no accounts, uploads, payments, or multi-tenancy. Its security
model assumes one trusted operator on their own machine.

## Reporting a vulnerability
Do not open a public issue for a security problem. Report privately via the
repository's "Report a vulnerability" (GitHub Security Advisories) or email the
maintainer. Include reproduction steps and impact. We aim to acknowledge within
a few days. Please do not test against systems you do not own.

## Supported versions
Only the latest release on the default branch is supported.

## Scope
In scope: the Python package, CLI, and local dashboard in this repository.
Out of scope: third-party sites it reads (GitHub, Hacker News, ATS providers),
and any deployment you build on top of it.

## Security posture (summary)
- Draft-only: never sends email/DMs, submits applications, opens PRs, pushes, or
  deploys. Those require explicit human action outside this tool.
- Secrets live in `.env` (gitignored); `.env.example` has placeholders only.
- All API writes are allowlist-validated with length caps.
- Scraped text is treated as untrusted and HTML-escaped.
- Outbound HTTP is limited to `http(s)` and blocks literal private/loopback hosts.
- Strict CSP, no CDN scripts (HTMX is vendored), generic error responses.
- CI runs secret scanning (gitleaks), dependency audit (pip-audit), and SAST
  (bandit).

See [`SECURITY_CHECKLIST.md`](SECURITY_CHECKLIST.md) for the full control triage
and [`THREAT_MODEL.md`](THREAT_MODEL.md) for threats and mitigations.

## Non-goals
We do not claim compliance with OWASP ASVS, ISO 27001, SOC 2, PCI DSS, GDPR, or
any other standard. Controls are chosen for a local tool, not an enterprise
service.
