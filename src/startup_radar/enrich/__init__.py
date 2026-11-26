"""Enrichment. Heuristics always run; the LLM layer is optional (Phase 4)."""

from .heuristics import extract_tags
from .llm import CostCaps, LLMAdapter, LLMCostExceeded, get_adapter, is_enabled

__all__ = [
    "extract_tags",
    "LLMCostExceeded",
    "LLMAdapter",
    "CostCaps",
    "get_adapter",
    "is_enabled",
]
