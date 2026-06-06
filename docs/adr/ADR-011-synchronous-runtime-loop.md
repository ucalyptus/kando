# ADR-011: Synchronous Runtime Event Loop

**Status:** Accepted  
**Date:** 2026-06-06

## Context

The runtime dispatches events to responders and processes their output sequentially via a `deque`. An async event loop was considered for allowing concurrent responder execution (e.g., multiple LLM calls in parallel).

## Decision

`Runtime.run()` is synchronous. The event loop is a `while queue: event = queue.popleft(); dispatch(event)` pattern. All responders run sequentially in registration order. The `LLMExecutorResponder` blocks on `llm_fn(...)` before yielding `llm.response`.

The MCP server wraps `Runtime.run()` in `asyncio.get_running_loop().run_in_executor(None, ...)` to avoid blocking the MCP event loop, but the runtime itself remains synchronous.

## Consequences

**Positive:**
- Deterministic execution order: same events always produce the same dispatch sequence.
- Simple mental model: no locks, no async context, no race conditions within a single run.
- Responders are plain synchronous functions — no `async def`, no `await`.
- The event queue is a single `deque` — no concurrent modification.

**Negative:**
- Multiple LLM calls within a run execute serially. A run with 3 questions makes 3 sequential LLM calls. Async would allow parallel execution (3x speedup).
- `llm_fn` must be synchronous. Async LLM SDKs require `asyncio.run()` or a thread bridge.
- Long-running `llm_fn` calls block the entire run. No progress is made on other events while an LLM is being called.

## Path to Async (Forward-Looking)

If parallel LLM calls become necessary:
1. Change `ResponderFn` to `AsyncResponderFn = Callable[[KandoEvent, World], AsyncIterator[KandoEvent]]`.
2. Change `Runtime.run()` to `async def run()` using `asyncio.gather()` for responders on the same event.
3. Move MCP server back to direct `await runtime.run()`.

This is a breaking change to the `Responder` interface and is deferred until performance profiling demonstrates the need.
