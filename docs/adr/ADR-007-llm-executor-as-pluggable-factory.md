# ADR-007: LLMExecutorResponder as a Pluggable Factory Function

**Status:** Accepted  
**Date:** 2026-06-06

## Context

The runtime needs to call LLMs but should not be coupled to a specific provider (Anthropic, OpenAI, local models, etc.). Several approaches were considered:

1. **Hardcode the Anthropic SDK** in the executor.
2. **Environment-variable-driven provider selection** (e.g., `KANDO_LLM_PROVIDER=anthropic`).
3. **Pluggable `llm_fn` callable** injected at runtime construction time.

## Decision

`LLMExecutorResponder(llm_fn: LLMFn) -> Responder` is a factory that wraps any callable matching:

```python
LLMFn = Callable[[list[dict], str, int], tuple[str, float]]
#                  messages    model  max_tokens   text  cost_usd
```

The executor is a plain `Responder` — it is added to the responder list alongside kit responders:

```python
responders = create_kit() + [LLMExecutorResponder(my_anthropic_fn)]
```

The executor also consults the `LLMCache` from `world.context["cache"]` before calling `llm_fn`. Cache key is SHA-256 of `{messages, model, max_tokens}`. On cache hit, the cached `(text, cost_usd)` is returned without calling the API. On miss, the result is stored.

## Consequences

**Positive:**
- Tests use a `fake_llm` function — no API calls, no mocking required.
- Provider can be swapped without touching any kit code.
- Cache integration is transparent to both kits and the `llm_fn` implementation.
- Adding retry logic, rate limiting, or observability is done in the `llm_fn` wrapper, not in the executor.

**Negative:**
- The `LLMFn` signature is synchronous. Async LLM SDKs require a sync wrapper (e.g., `asyncio.run()`). This is a consequence of the synchronous runtime loop (see ADR-011).
- `cost_usd` must be computed by the caller. If the caller doesn't know the cost (e.g., local models), it should return `0.0`.

## No Hard LLM Dependency in Core

`kando/` has zero LLM SDK dependencies. The `pyproject.toml` optional extras are intentionally empty for LLM SDKs — users bring their own.
