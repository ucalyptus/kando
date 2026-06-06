# ADR-005: Intention/Effect Split via llm.request / llm.response Events

**Status:** Accepted  
**Date:** 2026-06-06

## Context

The ESAA paper (arXiv 2602.23193) identifies "state drift" as a critical agent failure mode: agents believe they've completed tasks while actual effects haven't happened. It mandates that agents emit *structured intentions only*, with a separate deterministic orchestrator executing all effects.

Initial kit implementations made direct LLM calls inside responder `handle()` functions — collapsing the decision (what to ask) and the execution (actually calling the API) into one step. This meant:
- The log only recorded outcomes, not decisions.
- Replay reran the LLM call rather than serving the cached result.
- The cache was populated but never consulted.

## Decision

Kits emit `llm.request` events (structured intentions) rather than calling LLMs directly. A separate `LLMExecutorResponder` listens on `llm.request`, calls the actual LLM function, and emits `llm.response`. A third responder in each kit reads `llm.response` and updates the world via `OBJECT_PATCHED`.

The three-step chain:
```
responder → llm.request → LLMExecutorResponder → llm.response → kit responder → OBJECT_PATCHED
```

`llm.request` payload: `{messages, model, max_tokens, cause_object_id}`.  
`llm.response` payload: `{text, model, cost_usd, cause_object_id}`.

`cause_object_id` threads the causal link from the request through the response back to the world object being filled in.

## Consequences

**Positive:**
- Full audit trail: the log contains exactly what prompt was sent, to which model, with which parameters, and what came back.
- Replay is sound: on replay, the executor reads `llm.response` from the log (via cache) instead of hitting the API again.
- The budget enforcer can track LLM cost automatically from `llm.response.cost_usd`.
- Kits are decoupled from LLM providers: swap the executor, nothing in the kit changes.
- The executor is injected at runtime: `create_kit() + [LLMExecutorResponder(my_fn)]`.

**Negative:**
- Three-responder chain adds latency overhead (three event dispatches per LLM call).
- `cause_object_id` is a string convention, not a typed link — a typo silently produces a dangling reference.
- Without the executor wired in, `llm.request` events accumulate in the ledger with no response, and findings remain pending. This is a silent failure mode.

## Alternatives Rejected

- **Direct LLM calls in responders**: log records outcomes not decisions; cache is bypassed; replay reruns API calls.
- **Async executor**: the runtime loop is synchronous (ADR-011); async would require architectural changes.
