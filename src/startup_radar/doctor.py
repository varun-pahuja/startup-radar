"""Environment and config health checks."""

from __future__ import annotations

import sys
from dataclasses import dataclass

from sqlalchemy import text

from .config import get_settings, home, profile
from .db import get_engine, init_db


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def run_checks() -> list[Check]:
    checks: list[Check] = []
    settings = get_settings()

    checks.append(Check("python", sys.version_info >= (3, 11), sys.version.split()[0]))
    checks.append(Check("home", home().is_dir(), str(home())))

    prof = profile()
    checks.append(
        Check(
            "profile",
            bool(prof.get("demonstrated_stack")),
            f"{len(prof.get('demonstrated_stack') or [])} demonstrated skills",
        )
    )

    for name in ("sources", "scoring"):
        exists = (home() / "config" / f"{name}.yaml").exists()
        checks.append(Check(f"config:{name}", exists, "found" if exists else "missing"))

    try:
        init_db()
        with get_engine().connect() as conn:
            conn.execute(text("select 1"))
        checks.append(Check("database", True, "writable"))
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        checks.append(Check("database", False, str(exc)))

    checks.append(
        Check(
            "github_token",
            True,
            "set (5000 req/hr)" if settings.github_token else "optional; missing (60 req/hr)",
        )
    )

    if settings.llm_enabled:
        ready = bool(settings.llm_base_url and settings.llm_model)
        checks.append(
            Check("llm", ready, "configured" if ready else "enabled but base_url/model missing")
        )
    else:
        checks.append(Check("llm", True, "disabled (heuristics only)"))

    return checks
