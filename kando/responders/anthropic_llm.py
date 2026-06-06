"""Anthropic SDK implementation of LLMFn for use with LLMExecutorResponder."""
from __future__ import annotations

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def anthropic_llm(messages: list[dict], model: str, max_tokens: int) -> tuple[str, float]:
    response = _get_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
    )
    text = response.content[0].text
    # input/output token costs averaged at ~$0.25/MTok for haiku-class models
    cost_usd = (response.usage.input_tokens + response.usage.output_tokens) * 0.00000025
    return text, cost_usd
