# Sources policy

Startup Radar reads only public, permitted sources. It does not scrape sites
whose terms forbid automated access, and it never writes to third-party systems.

## Allowed
| Source | Method | Notes |
|---|---|---|
| GitHub | REST Search API | Issues with `good first issue` / `help wanted`; honours token rate limits. |
| Hacker News | Algolia Search API | Official "Who is hiring" threads. |
| Y Combinator | Public company/OSS data | Public listings only. |
| ATS providers | Public JSON (Ashby, Greenhouse, Lever, Workable) | Public job boards only. |
| RSS | Public feeds | Opt-in; disabled by default. |

## Excluded
- LinkedIn, Wellfound, Internshala, Cutshort — login-walled and/or terms forbid
  automated collection.
- Any site requiring bypassing authentication, CAPTCHAs, or robots rules.

## Rules
1. **Read-only.** No posting, messaging, applying, or account actions.
2. **Respect terms and `robots.txt`.** If a source forbids automation, do not add
   it.
3. **Be gentle.** Use caching and modest request volumes; set a `User-Agent`.
4. **Keep provenance.** Every stored row keeps its `source_url`, `fetched_at`,
   and `confidence`.
5. **No PII scraping.** Do not harvest personal emails or profiles from sites
   that prohibit it; use only what the source publishes for this purpose.
6. **Rate limits.** Prefer an authenticated GitHub token (higher limits) and
   cache responses.

## Adding a source
Add an adapter in `src/startup_radar/sources/`, register it, document it here,
and confirm its terms permit read-only automated access. Do not add a source that
requires a login or violates its terms.
