"""OpenRouter implementation of LLMFn for LLMExecutorResponder."""
from __future__ import annotations

import os

import httpx

# Kit model names are Anthropic-format; OPENROUTER_MODEL overrides globally.
_DEFAULT_MODEL = "anthropic/claude-haiku-4-5"

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=60.0)
    return _client


def openrouter_llm(messages: list[dict], model: str, max_tokens: int) -> tuple[str, float]:
    or_model = os.environ.get("OPENROUTER_MODEL", _DEFAULT_MODEL)
    resp = _get_client().post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
        json={"model": or_model, "max_tokens": max_tokens, "messages": messages},
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    cost_usd = (usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)) * 0.00000025
    return text, cost_usd
