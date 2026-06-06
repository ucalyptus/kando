# ADR-012: Hash-Verified Replay (Proposed)

**Status:** Proposed  
**Date:** 2026-06-06

## Context

The ESAA paper (arXiv 2602.23193) requires that replaying the event log produces identical SHA-256 hashes on materialized projections. This provides a cryptographic guarantee that the world derived from the log is correct and has not diverged.

Currently, `runtime.replay(strict=True)` re-runs seed events through responders and returns the resulting world, but does NOT compare it to the permissive projection. There is no divergence signal. The strict replay budget allows 2x the original event count without detecting overproduction.

## Proposed Decision

1. **Hash the world after every run.** `Runtime.run()` should compute a `world_hash` before returning:
   ```python
   def _hash_world(world: World) -> str:
       payload = json.dumps({
           "objects": {k: v.data for k, v in sorted(world.objects.items())},
           "relations": {k: {"type": r.type, "source_id": r.source_id, "target_id": r.target_id}
                         for k, r in sorted(world.relations.items())},
       }, sort_keys=True)
       return hashlib.sha256(payload.encode()).hexdigest()
   ```
   Store this hash as a `RUN_COMPLETED` event in the ledger.

2. **Verify on strict replay.** `replay(strict=True)` should:
   - Run the strict replay to produce `strict_world`.
   - Reproject the ledger to produce `permissive_world`.
   - Hash both and compare. Return `ReplayResult(world, diverged: bool, hash_expected, hash_actual)`.
   - Set budget to `max_events=len(original_events)` (not 2x) to detect overproduction.

3. **Store snapshots with hash.** `save_snapshot()` should include the world hash alongside the serialized state. On load, verify the hash before trusting the snapshot.

## Consequences

**Positive:**
- Cryptographic guarantee: strict replay divergence is detectable, not just observable.
- Snapshot integrity: corrupt or stale snapshots are rejected rather than silently used.
- Enables fork verification: two branches forked from the same prefix should have identical world hashes up to the fork point.

**Negative:**
- World hashing requires stable JSON serialization (sorted keys, stable float representation). Non-deterministic values (timestamps, UUIDs in data payloads) must be excluded from the hash.
- UUID-based event IDs (ADR-008) mean event IDs are non-deterministic across replays — the hash must cover world *data*, not event IDs.
- Performance cost: hashing a large world adds latency to every run completion.

## Prerequisite

ADR-008 (UUID IDs) must be in place — the hash must be over world shape, not event IDs.

## Not Yet Implemented
