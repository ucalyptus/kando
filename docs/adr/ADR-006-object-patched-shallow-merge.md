# ADR-006: OBJECT_PATCHED Uses Shallow Merge

**Status:** Accepted  
**Date:** 2026-06-06

## Context

When an LLM fills in a pending Finding or Claim, the world object needs to be updated. Two event strategies were considered:

1. **Re-emit OBJECT_CREATED** with the same `id` — last-write-wins via projection overwrite.
2. **Emit OBJECT_PATCHED** with a diff — patch applied in-place.

Both work because `apply()` handles duplicate `OBJECT_CREATED` IDs by overwriting (`world.objects[id] = ...`) and handles `OBJECT_PATCHED` via `obj.data.update(patch)`.

## Decision

Kits use `OBJECT_PATCHED` to update pending objects. `apply()` implements `OBJECT_PATCHED` as a **shallow merge** via `dict.update()`:

```python
obj.data.update(copy.deepcopy(event.data.get("patch", {})))
```

The patch is deep-copied before merging to prevent aliasing.

## Consequences

**Positive:**
- `OBJECT_PATCHED` preserves the original `OBJECT_CREATED` in the ledger — the history is richer than re-emitting.
- Patch events are small: only changed fields are transmitted.
- The original creation timestamp and ID are preserved.

**Negative:**
- **Shallow merge only**: patching `{"config": {"a": 1}}` over `{"config": {"a": 0, "b": 2}}` produces `{"config": {"a": 1}}` — key `b` is silently lost. Any responder patching nested dicts expecting deep merge will get incorrect results.
- This semantic must be documented at every patch call site and in kit documentation.

## Decision: Accept Shallow Merge

Deep merge adds complexity (recursive merge logic, merge conflict resolution). All current patch operations replace leaf fields (`text`, `status`, `summary`) — no nested dict merges occur. If nested patch semantics are needed in future, introduce `OBJECT_DEEP_PATCHED` with RFC 7396 JSON Merge Patch semantics.

## Convention

Patches should only target leaf fields. Do not patch a dict-valued field expecting the sub-keys to merge.
