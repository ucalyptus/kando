# ADR-001: Event Log as Source of Truth

**Status:** Accepted  
**Date:** 2026-06-06

## Context

Traditional agent frameworks hold mutable state in memory, databases, or files. This makes debugging hard (the state at the time of a failure is gone), forking expensive (you must clone the full state), and replay impossible (you have no record of what happened).

The "Log is the Agent" paper (arXiv 2605.21997) and ESAA (arXiv 2602.23193) both argue that the append-only event log should be the primary data structure, with the current world state derived as a projection of it.

## Decision

The append-only `LedgerStore` is the single source of truth for every Kando run. No state is written anywhere except through `ledger.append()`. The in-memory `World` is a cache — it is always reconstructible from the ledger via `project(ledger.read_all())`. This is enforced by the `Runtime`: every event is appended to the ledger before being applied to the world.

## Consequences

**Positive:**
- Deterministic replay is free: reproject the ledger → identical world.
- Cheap forking: fork at position N, share prefix, replay only the divergent tail.
- Full causal lineage: every event carries `cause: list[str]` linking it to its parent events, giving a complete DAG of the run.
- Post-mortem debugging: the ledger of a failed run survives the failure and can be inspected offline.

**Negative:**
- The world is rebuilt from scratch on `runtime.load()` — no incremental update path yet (snapshot integration is a future optimization, see ADR-003 and ADR-012).
- Event IDs must be globally unique within a ledger; any counter-sharing across runs violates this (fixed by ADR-008).
- Events are immutable records; updating a world object requires a new event (OBJECT_PATCHED), not a mutation.

## References

- arXiv 2605.21997 — "The Log is the Agent"
- arXiv 2602.23193 — "ESAA: Event Sourcing for Autonomous Agents"
