"""Draft-only outreach (Phase 5).

Two hard rules from MASTER_PROMPT.md: nothing is ever sent from here, and no
email address is ever guessed. `draft` builds text, `eml` writes a file you
open in your own mail client, `followup` only tracks when to nudge.
"""

from .draft import draft
from .eml import export, render
from .followup import due, followup_count, mark_sent, record

__all__ = [
    "draft",
    "export",
    "render",
    "due",
    "followup_count",
    "mark_sent",
    "record",
]
