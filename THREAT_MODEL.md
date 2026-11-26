# Threat model

## Assets
- GitHub token and optional LLM API key (in `.env`).
- The local SQLite database (`data/startup_radar.db`) and the personal profile
  (`config/profile.yaml`).
- Integrity of the opportunities shown (no fabricated rows).

## Actors
- The local operator (trusted).
- Remote content authors (untrusted): GitHub issue text, HN comments, ATS/RSS
  content, and any config-supplied URL.
- A network attacker on the local machine or LAN (limited: server binds to
  loopback).

## Trust boundaries
1. **Remote HTTP → parser**: all fetched text is untrusted.
2. **Parser → database**: values are length-capped and stored as data.
3. **Database → HTML**: rendered with Jinja autoescape; URLs forced to `http(s)`.
4. **Browser → local API**: same-origin only; writes allowlist-validated.
5. **Config → outbound HTTP**: URLs pass the SSRF guard.

## STRIDE summary

| Threat | Example | Mitigation |
|---|---|---|
| Spoofing | Fake job posting | Provenance columns (`source_url`, `fetched_at`, `confidence`); honesty rules |
| Tampering | Malicious issue text altering UI | Autoescape + CSP; no `\|safe` |
| Repudiation | "I never applied" | `activity_log` records actions |
| Information disclosure | Token leaking | `.env` gitignored; no secrets in logs; gitleaks in CI |
| Denial of service | Huge request | 1 MB body cap; row limits |
| Elevation of privilege | SSRF to internal services | `ensure_safe_url` blocks private/loopback/non-HTTP |
| XSS | `<script>` in a scraped title | Autoescape + strict CSP (no inline/CDN) |
| Prompt injection | Issue text telling the LLM to exfiltrate | Treated as data; see `AI_SECURITY.md` |

## Explicitly accepted risks
- Local HTTP (no TLS) on loopback.
- No authentication: anyone with local access to the machine can use it.
- DNS names resolving to private IPs bypass the literal-IP SSRF check.
- The LLM, when enabled, sends selected text to a third-party endpoint the user
  configures.
