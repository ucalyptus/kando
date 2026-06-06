# ADR-013: Schema Boundary Contracts on Responder Output (Proposed)

**Status:** Proposed  
**Date:** 2026-06-06

## Context

The ESAA paper requires JSON schema contracts per event type. Violations should emit `output.rejected` events rather than crashing. Currently, `KandoEvent.data` is `dict[str, Any]` — no validation occurs at dispatch time. A responder that emits an `OBJECT_CREATED` event missing the `"id"` key will cause `apply()` to raise `KeyError`, crashing the runtime loop.

## Proposed Decision

Add per-type payload validation in `runtime._dispatch()` before dispatching to responders:

```python
def _dispatch(self, event, world, queue):
    validation_error = validate_event(event)
    if validation_error:
        queue.append(make_rejection_event(event, validation_error))
        return
    # ... existing dispatch logic
```

`validate_event(event)` checks required keys per event type:

| Event type | Required payload keys |
|---|---|
| `object.created` | `id`, `type` |
| `object.patched` | `id`, `patch` |
| `relation.created` | `id`, `type`, `source_id`, `target_id` |
| `llm.request` | `messages`, `model`, `max_tokens` |
| `llm.response` | `text`, `model`, `cost_usd` |

Violations emit `output.rejected` with `{original_event_id, reason}` and continue processing. They do NOT crash the loop.

Also add `__post_init__` validation to `KandoEvent` itself for top-level required fields (`id`, `type`, `source`, `actor`, `cause`, `timestamp`).

## Consequences

**Positive:**
- Runtime loop never crashes on malformed responder output — it emits `output.rejected` and continues.
- `output.rejected` events are auditable in the ledger: debugging malformed events is possible post-run.
- Satisfies the ESAA boundary contract requirement.

**Negative:**
- Validation adds per-event overhead (dict key lookups).
- Schema must be kept in sync with `apply()` — a mismatch between what validation allows and what `apply()` expects is a new failure mode.
- Validation only covers required *keys*, not value types. Full JSON Schema validation would be more correct but adds a dependency.

## Not Yet Implemented
