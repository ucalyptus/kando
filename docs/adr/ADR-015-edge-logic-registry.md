# ADR-015: Edge Logic Registry — Global Registry, Acknowledged Limitation

**Status:** Accepted with Known Limitation  
**Date:** 2026-06-06

## Context

`kando/responders/edge.py` maintains a module-level `_registry: dict[str, EdgeLogicFn]` populated via the `@edge_logic(relation_type)` decorator. `Runtime._dispatch()` calls `edge_logic.dispatch(event, world)` for every event.

**Known problems with the global registry:**
1. No kit currently uses `@edge_logic` — it is dead code in the dispatch path (every event checks it with zero registered handlers).
2. If two kits register handlers for the same `relation_type`, the second silently overwrites the first (now emits a `warnings.warn` after the gap-fixing pass).
3. In a multi-tenant process, any kit that registers edge logic at import time pollutes all Runtime instances.

## Decision

Keep the global registry for now, with these mitigations:
- Add `warnings.warn` on duplicate registration (implemented).
- Document that `@edge_logic` is process-global and incompatible with multi-tenant use.

Do NOT use `@edge_logic` in any kit until the registry is made instance-scoped.

## Forward-Looking

The correct fix is to make `_registry` an instance variable on a class:

```python
class EdgeLogicRegistry:
    def __init__(self): self._registry = {}
    def register(self, relation_type, fn): ...
    def dispatch(self, event, world): ...
```

`Runtime.__init__` accepts an optional `EdgeLogicRegistry`. Kits that need edge logic construct one and pass it to `Runtime`. This eliminates the global state entirely.

This change is deferred because `@edge_logic` is currently unused. When the first kit uses it, the registry should be made instance-scoped at that time.

## Current State

`edge_logic.dispatch()` is called on every event with zero registered handlers — it is a no-op with one dict lookup overhead per event. This is negligible but should be removed from the dispatch hot path if it remains unused.
