# ADR-009: LLMCache Injected via world.context

**Status:** Accepted  
**Date:** 2026-06-06

## Context

The `LLMCache` is a content-addressed dict keyed by normalized request hash. It must be accessible to the executor responder during event dispatch. Two approaches were considered:

1. **Pass cache directly to each responder**: changes the `Responder` interface and `ResponderFn` signature.
2. **Inject via `world.context`**: the runtime sets `world.context["cache"] = self._cache` in `Runtime.load()`; responders read it from there.

## Decision

`world.context` is a free-form dict attached to every `World` instance. The runtime injects the `LLMCache` there at load time. Responders that need the cache read `world.context.get("cache")`.

The `LLMExecutorResponder` uses the cache as follows:
- Compute SHA-256 key over `{messages, model, max_tokens}` (JSON-serialized, sorted keys).
- `cache.get(request_dict)` → returns `(text, cost_usd)` or `None`.
- On miss: call `llm_fn`, then `cache.put(request_dict, (text, cost_usd))`.
- On hit: return cached result; emit `llm.response` with `cost_usd=0.0` (no new API cost).

## Consequences

**Positive:**
- `Responder` interface unchanged — adding cache access is opt-in per responder.
- `world.context` is already a general-purpose side-channel; using it for cache is consistent.
- Cache is available throughout the lifetime of a `World` including in `reproject()` paths if the caller sets `world.context["cache"]` before projecting.

**Negative:**
- `world.context` is untyped (`dict[str, Any]`) — accessing a missing key silently returns `None` if using `.get()`. A typo in the key name fails silently.
- The cache is not serialized with the world (see ADR-003). On cold load from ledger, the cache starts empty even if a prior run populated it. This means strict cold replay will re-execute cached LLM calls unless the cache is explicitly restored.

## Cache Semantics

The cache is content-addressed and idempotent. Putting the same key twice overwrites silently (last-write-wins). The cache does not expire — for long-running processes, memory growth is unbounded. A future `ScopedLLMCache` subclass can add TTL or LRU eviction.
