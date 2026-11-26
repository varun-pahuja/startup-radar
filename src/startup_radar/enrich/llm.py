"""LLM enrichment adapter (Phase 4). Uses litellm for OpenAI-compatible endpoints.

Cost caps are enforced per-run; exceeding them disables LLM for that run and
falls back to heuristics-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import litellm
except ImportError:
    litellm = None  # type: ignore[assignment]

from ..config import llm as llm_cfg


@dataclass(slots=True)
class CostCaps:
    max_requests_per_run: int = 50
    max_tokens_per_run: int = 200_000
    max_input_tokens_per_call: int = 8_000
    max_output_tokens_per_call: int = 2_000

    @classmethod
    def from_config(cls) -> CostCaps:
        cfg = llm_cfg()
        caps_cfg = cfg.get("cost_caps") or {}
        return cls(
            max_requests_per_run=caps_cfg.get("max_requests_per_run", 50),
            max_tokens_per_run=caps_cfg.get("max_tokens_per_run", 200_000),
            max_input_tokens_per_call=caps_cfg.get("max_input_tokens_per_call", 8_000),
            max_output_tokens_per_call=caps_cfg.get("max_output_tokens_per_call", 2_000),
        )


class LLMCostExceeded(Exception):
    """Raised when a cost cap would be exceeded."""


class LLMAdapter:
    """Thin wrapper around litellm with cost caps and structured output."""

    def __init__(self, caps: CostCaps | None = None) -> None:
        if litellm is None:
            raise RuntimeError("litellm not installed")
        self._caps = caps or CostCaps.from_config()
        self._requests = 0
        self._input_tokens = 0
        self._output_tokens = 0

    def _check_caps(self, estimated_input: int, max_output: int) -> None:
        if self._requests >= self._caps.max_requests_per_run:
            raise LLMCostExceeded(f"request cap ({self._caps.max_requests_per_run})")
        if self._input_tokens + estimated_input > self._caps.max_tokens_per_run:
            raise LLMCostExceeded(f"input token cap ({self._caps.max_tokens_per_run})")
        if self._output_tokens + max_output > self._caps.max_tokens_per_run:
            raise LLMCostExceeded(f"output token cap ({self._caps.max_tokens_per_run})")
        if estimated_input > self._caps.max_input_tokens_per_call:
            raise LLMCostExceeded(f"per-call input cap ({self._caps.max_input_tokens_per_call})")
        if max_output > self._caps.max_output_tokens_per_call:
            raise LLMCostExceeded(f"per-call output cap ({self._caps.max_output_tokens_per_call})")

    def _count_tokens(self, text: str) -> int:
        # rough heuristic: ~4 chars/token for English
        return max(1, len(text) // 4)

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | dict[str, Any]:
        """Call the model. Returns str or parsed dict if json_schema given."""
        cfg = llm_cfg()
        model = cfg.get("model") or ""
        if not model:
            raise RuntimeError("LLM model not configured")
        base_url = cfg.get("llm_base_url") or ""
        api_key = cfg.get("llm_api_key") or ""
        temperature = temperature if temperature is not None else cfg.get("temperature", 0.2)
        max_tokens = max_tokens or cfg.get("max_tokens", 800)

        estimated_input = self._count_tokens(system + user)
        self._check_caps(estimated_input, max_tokens)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if base_url:
            kwargs["api_base"] = base_url
        if api_key:
            kwargs["api_key"] = api_key
        if json_schema:
            kwargs["response_format"] = {"type": "json_schema", "json_schema": json_schema}

        resp = litellm.completion(**kwargs)
        content = resp.choices[0].message.content or ""
        self._requests += 1
        usage = getattr(resp, "usage", None)
        if usage:
            self._input_tokens += usage.prompt_tokens
            self._output_tokens += usage.completion_tokens
        else:
            # fallback estimate
            self._input_tokens += estimated_input
            self._output_tokens += self._count_tokens(content)

        if json_schema:
            import json
            return json.loads(content)
        return content


def is_enabled() -> bool:
    return llm_cfg().get("enabled", False)


def get_adapter(caps: CostCaps | None = None) -> LLMAdapter | None:
    if not is_enabled():
        return None
    return LLMAdapter(caps or CostCaps.from_config())