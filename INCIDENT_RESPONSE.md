# Incident response (local tool)

Short runbooks for the realistic incidents for a local, single-user tool.

## 1. A token or key leaked
Signs: a secret committed, pasted, or exposed in a log.
1. **Revoke immediately** at the provider (GitHub → Settings → Developer settings
   → Tokens; LLM provider console).
2. Issue a new token and put it in `.env` (never in code or config).
3. If it reached git history, treat it as public: revoke first, then clean
   history (e.g. `git filter-repo`) before any push.
4. Check provider audit logs for unexpected use.

## 2. Secret accidentally staged for commit
1. `git restore --staged .env` (and any file with secrets).
2. Confirm `.gitignore` covers it.
3. If already committed locally but not pushed, amend/rewrite before pushing.
4. Rotate the secret anyway if unsure.

## 3. Malicious/scraped content caused a problem (XSS, prompt injection)
1. Do not click through suspicious links; inspect the source row.
2. Delete the row or disable the source in `config/sources.yaml`.
3. The dashboard escapes HTML and forces `http(s)` links, and the CSP blocks
   inline/external script; if you find a bypass, file a private report
   (see `SECURITY.md`).

## 4. Dependency vulnerability reported
1. Reproduce with `pip-audit` / `bandit`.
2. Update the affected package; run `ruff`, `mypy`, `pytest`.
3. If no fix exists, document the exposure and whether the vulnerable path is
   reachable in this tool.

## 5. Local data loss
1. Restore `data/startup_radar.db` from backup (it is a single file).
2. Re-run `startup-radar discover && rank && report` if needed.

## After any incident
Record what happened, the root cause, and the fix in `DECISIONS.md` or the
changelog. Do not claim a fix without verifying it.
