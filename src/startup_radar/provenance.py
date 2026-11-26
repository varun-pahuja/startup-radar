"""Provenance helpers — the honesty layer.

Every evidence row carries source_url, fetched_at, confidence. Nothing is
presented as fact without them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

UNKNOWN = "Unknown"
NOT_PUBLIC = "Not Publicly Available"


class Confidence(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


def utcnow() -> datetime:
    return datetime.now(UTC)


def now_iso() -> str:
    return utcnow().isoformat()
