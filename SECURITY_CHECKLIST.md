# Security checklist — triage for Startup Radar

This maps an enterprise web/AI security checklist onto **this project**. Startup
Radar is a **local, single-user, localhost-only** research tool: no accounts, no
sessions, no uploads, no payments, no multi-tenancy, no public deployment by
default. Most enterprise controls do not apply. We do not claim compliance with
any framework.

Legend: **Implemented** · **Partial** · **N/A** (not applicable, reason given) ·
**Follow-up** (needed only if the tool is hosted or made multi-user).

## Scope and trust model (short)

- Runs on `127.0.0.1`; the user is the only principal.
- Untrusted input = scraped GitHub/HN/ATS text and any config-supplied URL.
- Secrets = GitHub token and optional LLM key, in `.env` (gitignored).
- Data = local SQLite under `data/` (gitignored).
- No outbound action except read-only HTTP GETs to allowlisted sources.

## 1. Authentication and session security — N/A
No login, accounts, or sessions exist. If hosted/multi-user: add OIDC or passkeys,
server-side sessions, MFA, secure/HttpOnly/SameSite cookies. Tracked as Follow-up.

## 2. Authorization (RBAC / ABAC / tenancy) — N/A
Single local user; no roles, no tenants, no row-level authorization. All API
writes are validated by allowlists. If multi-tenant: add tenant scoping + RLS.

## 3. Input / output and injection — Partial (core done)
- SQL injection: **Implemented** — SQLAlchemy ORM parameterised queries only; no
  string-built SQL.
- XSS: **Implemented** — Jinja2 autoescape on `.html`; `safe_url` filter forces
  `http(s)` only; no `|safe`; no inline scripts; CSP blocks external/inline script.
- Command injection: **Implemented** — no shell/subprocess execution anywhere.
- SSRF: **Implemented** — `http.ensure_safe_url` blocks non-HTTP(S) schemes and
  literal private/loopback/link-local/reserved hosts before every request.
- Open redirect: **Implemented** — redirects only to fixed internal paths.
- Header injection: **Implemented** — framework-managed response headers.
- Insecure deserialisation: **Implemented** — JSON/YAML-safe load only; no pickle.
- Path traversal: **N/A** — no user-controlled file paths; static dir is fixed.

## 4. HTTP headers and transport — Implemented (localhost)
`web/app.py` middleware sets: CSP (`default-src 'self'`, no `unsafe-inline`,
`frame-ancestors 'none'`, `base-uri 'none'`, `form-action 'self'`),
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy:
no-referrer`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`,
`Cross-Origin-Resource-Policy`, `Cache-Control: no-store`, and HSTS **only** over
HTTPS. Server banner suppressed (`server_header=False`). TLS itself is N/A on
localhost; required if hosted (Follow-up).

## 5. Cookies and client-side sessions — N/A
No cookies or client sessions. No sensitive data in `localStorage`.

## 6. API security — Partial
- Request size limit: **Implemented** (1 MB, 413).
- CORS: **Implemented** by absence — no CORS middleware, so same-origin only.
- Rate limiting: **N/A** on localhost single-user; add if hosted (Follow-up).
- Mass assignment: **Implemented** — every writable field validated against an
  allowlist with length caps (`web/app.py`).
- Pagination / result caps: **Implemented** — row limit 500 on the main sheet.
- API docs disabled (`docs_url=None`, `redoc_url=None`).

## 7. Database and data storage — Partial
- Parameterised access: **Implemented** (ORM).
- Credentials in code: **Implemented** — none; DB URL from env.
- At-rest encryption / RLS: **N/A** for a local SQLite file. Recommendation:
  rely on OS full-disk encryption. If hosted: managed DB with encryption + RLS.

## 8. Secrets management — Implemented
- `.env` gitignored; `.env.example` holds only placeholders.
- No hardcoded tokens; all secrets read from env (`config.py`).
- CI secret scanning via gitleaks (`.github/workflows/security.yml`).
- Never logged (no secret-bearing log statements).

## 9. File upload security — N/A
No upload endpoints.

## 10. WAF / DDoS / network perimeter — N/A
Localhost only. If hosted: TLS termination, reverse proxy, rate limits, WAF.

## 11. Frontend / client-side — Implemented
No secrets or tokens in the browser; HTMX is **vendored** locally
(`web/static/htmx.min.js`) so there is no third-party CDN script; CSP has no
`unsafe-inline`/`unsafe-eval`.

## 12. LLM / AI application security — Partial (planned, Phase 4)
LLM enrichment is off by default (`LLM_ENABLED=false`). Guardrails are specified
in [`AI_SECURITY.md`](AI_SECURITY.md): scraped text is untrusted data (never
instructions), no secrets in prompts, structured-output validation, no tool
execution, and cost caps. Implemented when the adapter lands.

## 13. Agentic / autonomous behaviour — Partial
There is no autonomous runtime agent. Outreach is **draft-only**; nothing is
sent, applied, pushed, or deployed without explicit human approval. Documented
in `AGENTS.md` and `AI_SECURITY.md`.

## 14. RAG / vector store — N/A
No vector database or retrieval pipeline.

## 15. AI cost and rate controls — Follow-up (Phase 4)
Token/request caps and a kill switch will ship with the LLM adapter.

## 16. Third-party integrations — Partial
Only read-only public APIs (GitHub, HN Algolia, ATS JSON, RSS). No OAuth, no
write scopes. Source allowlist and ToS rules in
[`docs/sources-policy.md`](docs/sources-policy.md).

## 17. Supply chain — Implemented
- `pip-audit` in CI and locally: **no known vulnerabilities** (verified
  2026-11-26).
- `bandit` SAST in CI: **clean** after replacing `sha1` with `sha256` for
  non-security hashing.
- Dependabot for pip + GitHub Actions (`.github/dependabot.yml`).
- **Follow-up:** generate an SBOM and pin Actions to commit SHAs.

## 18. DevSecOps / CI — Implemented
Separate `security` workflow (secrets, dependency audit, SAST) plus the existing
lint/type/test CI. Actions currently pinned to major tags; pinning to SHAs is a
Follow-up.

## 19. Logging and monitoring — Partial
No secrets or PII logged; an in-app `activity_log` table records user actions.
Centralised monitoring is N/A for a local tool.

## 20. Error handling — Implemented
Generic `500` JSON handler returns no tracebacks or internals; validation errors
return `422` with safe messages.

## 21. Privacy — Implemented
Local-only, no telemetry. See [`PRIVACY.md`](PRIVACY.md). Data deletion = remove
`data/` and `config/profile.yaml`.

## 22. Backup and recovery — Partial
SQLite file is a single portable file; back up `data/startup_radar.db`. No
automated backups (out of scope for local use).

## 23. Security testing — Implemented
`tests/integration/test_security.py` asserts: security headers present, scraped
titles escaped, dangerous URL schemes neutralised, SSRF guard blocks
private/loopback/non-HTTP targets, oversized requests rejected, and API writes
reject invalid values.

## 24. Security tooling — Implemented (minimal, deliberate)
gitleaks + pip-audit + bandit + Dependabot. Heavier platforms (SonarQube, ZAP,
SIEM) are intentionally omitted as overkill for a local tool.

## 25. Standards alignment — Reference only
Informed by OWASP Top 10 / ASVS, OWASP LLM Top 10, and NIST SSDF. **No
certification or compliance claim is made.**

## 26. Documentation — Implemented
`SECURITY.md`, `THREAT_MODEL.md`, `AI_SECURITY.md`, `PRIVACY.md`,
`INCIDENT_RESPONSE.md`, `ARCHITECTURE.md`, this file, and
`docs/sources-policy.md`.

## 27. Audit workflow — N/A
This section targets auditing a foreign codebase. Here we implemented controls
directly against our own code.

## 28. Final report — See "Implemented in code" below

## Implemented in code (evidence)

| Control | Location |
|---|---|
| Security headers + CSP + HSTS-on-https + body limit | `src/startup_radar/web/app.py` |
| Generic error handler (no tracebacks) | `src/startup_radar/web/app.py` |
| Input allowlists + length caps | `src/startup_radar/web/app.py` |
| `http(s)`-only link filter | `src/startup_radar/web/app.py` + templates |
| SSRF guard | `src/startup_radar/http.py` |
| No server banner | `src/startup_radar/cli.py` (`server_header=False`) |
| Vendored HTMX (no CDN) | `src/startup_radar/web/static/htmx.min.js` |
| Secret/dep/SAST CI | `.github/workflows/security.yml` |
| Dependabot | `.github/dependabot.yml` |
| Security regression tests | `tests/integration/test_security.py` |

## Residual risks / follow-ups
- Hosted or multi-user deployment would require auth, sessions, RBAC/tenancy,
  TLS, rate limiting, and RLS — all currently N/A by design.
- DNS names that resolve to private IPs are not caught by the SSRF guard
  (literal-IP and scheme checks only).
- GitHub Actions are pinned to tags, not commit SHAs.
- `sha256` content hashing changed dedupe keys; rebuild the dev DB after upgrade.
