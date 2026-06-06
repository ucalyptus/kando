# ADR-008: UUID-Based Event IDs

**Status:** Accepted  
**Date:** 2026-06-06  
**Supersedes:** Sequential global counter approach

## Context

The original `make_event()` accepted `run_id_counter: int` and produced IDs like `"object.created-5"`. The counter was a module-level global in each kit and in `LLMExecutorResponder`.

This caused three critical problems:

1. **Replay soundness**: on `replay(strict=True)`, kit counters were already advanced from the original run, so every replayed event got a different ID. The strict replay produced a structurally different world with different object IDs.
2. **Test isolation**: tests sharing a process shared counter state. A test that expected `"finding-3"` would get `"finding-8"` if run after other tests.
3. **Concurrency hazard**: two concurrent runs in the same process raced on `global _COUNTER; _COUNTER += 1` (non-atomic read-modify-write under the GIL).

## Decision

`make_event()` generates event IDs using `uuid.uuid4().hex[:8]` suffixes:

```python
id=f"{type}-{uuid.uuid4().hex[:8]}"
```

The `run_id_counter` parameter is removed. All kit-level `_COUNTER` globals and `_next_id()` functions are removed. Object IDs within kits also use `uuid.uuid4().hex[:8]` suffixes.

## Consequences

**Positive:**
- Replay soundness restored: IDs are independent of process state.
- Test isolation restored: no shared counter between tests.
- Concurrency safe: `uuid.uuid4()` is thread-safe.
- IDs are opaque and don't embed redundant type information.

**Negative:**
- IDs are no longer sequential — you cannot infer creation order from ID alone. Use `event.timestamp` or ledger position for ordering.
- IDs are not fully deterministic: two identical runs produce different event IDs. Determinism is preserved at the *world shape* level (same objects, same data) not at the *ID* level. Strict replay verifies world shape equality, not ID equality.
- Short UUID suffix (8 hex chars = 32 bits) has birthday collision probability of ~1 in 65k at 100 events per run. Acceptable for current scale; extend to 16 chars if ledgers grow large.

## Note on Strict Replay

Because IDs are non-deterministic, strict replay cannot compare event IDs. It must compare world *shape* (same objects, same data, same relations). The `diff()` function in `kando/branch/` is the correct tool for this comparison. See ADR-013 for the forward-looking hash-verified replay design.
