"""The Source protocol and the neutral record every adapter returns."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass
class RawOpportunity:
    kind: str  # job | internship | oss_issue | product_problem
    title: str
    url: str
    source: str
    company_name: str = ""
    company_domain: str | None = None
    company_url: str = ""
    description: str = ""
    stack: list[str] = field(default_factory=list)
    posted_at: datetime | None = None
    location: str = ""
    remote: bool = False
    confidence: str = "unverified"
    payload: dict[str, Any] = field(default_factory=dict)


class Source(Protocol):
    name: str

    def fetch(self, cfg: dict[str, Any]) -> Iterable[RawOpportunity]: ...
