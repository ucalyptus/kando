# ADR-010: Branch/Fork via Ledger Prefix + LLM Cache

**Status:** Accepted  
**Date:** 2026-06-06

## Context

A key property claimed by "The Log is the Agent" (arXiv 2605.21997) is cheap forking: branch a run at any event without re-executing shared computation. The naive approach (clone the full state and replay from scratch) is O(n) in run length for every fork.

## Decision

Forking works as follows:

1. `fork(run_id, position)` records a `BranchMeta(parent_run_id, fork_position)` and creates a new ledger stream named `branch:{branch_id}`.
2. On replay of the branch, the shared prefix (events 0..fork_position) is served from the `LLMCache` — LLM calls made in the prefix are cache hits, so no API calls are re-executed.
3. Only the divergent tail (events after fork_position) executes against live responders.

`diff(world_a, world_b)` compares two worlds (from different branches or runs) and returns `{added, removed, patched}` sets of objects and relations.

## Consequences

**Positive:**
- Forking is O(tail_length) in execution cost, not O(total_run_length).
- The `BranchMeta` is recorded as a `BRANCH_CREATED` event in the parent ledger, making the branch relationship auditable.
- `diff()` enables comparing alternative futures: "what would have happened if I had asked a different question?"

**Negative:**
- Cache must be warm for the prefix to be cheap. Cold replays (new process, cache evicted) still pay O(n) in LLM calls for the prefix.
- The cache is in-memory — it does not persist across process restarts. A persistent cache (Redis, disk) would be needed for long-lived fork trees.
- `diff()` compares world *shapes* (object data equality), not event histories. Two worlds can have the same objects with different causal histories — `diff()` does not detect this.

## Forward-Looking

Hash-verified replay (ADR-013) would allow the fork prefix to be verified cryptographically rather than relying on cache correctness.
