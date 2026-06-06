# ADR-002: Responder Pattern (No Central Orchestrator)

**Status:** Accepted  
**Date:** 2026-06-06

## Context

Agent frameworks typically have a central orchestrator or router that decides what to run next. This creates a bottleneck, hides coordination logic in one place, and makes it difficult to add new behaviors without modifying the core.

## Decision

Coordination is emergent, not explicit. Every behavior in Kando is a `Responder` — a named function subscribed to a `frozenset` of event types. When an event is dispatched, ALL matching responders fire and yield new events. No responder calls another directly. The runtime's exhaustion-driven loop continues until the event queue is empty.

```
event → all matching responders → new events → enqueued → repeat
```

Responders are registered at construction time and passed to `Runtime`. The runtime is agnostic to domain logic.

## Consequences

**Positive:**
- Adding behavior is additive: register a new responder, nothing else changes.
- No responder knows about any other responder — no coupling.
- Coordination logic is co-located with its semantic meaning (e.g., the research kit's synthesis responder knows when to synthesize).
- Testable in isolation: a responder is a pure function `(event, world) → Iterator[event]`.

**Negative:**
- Execution order between responders on the same event is deterministic only by registration order. Behavior that depends on order between siblings is fragile.
- Debugging "why did X fire" requires tracing through the event queue, not following a call stack.
- There is no built-in mechanism to prevent responder output loops (a responder that fires on its own output). The budget enforcer is the backstop.

## Alternatives Rejected

- **Central orchestrator**: requires modifying core to add behaviors; creates a god object.
- **Direct responder-to-responder calls**: introduces coupling and breaks the log-as-truth invariant (calls produce no events).
