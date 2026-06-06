# ADR-014: Multi-Agent Concurrency Safety (Proposed)

**Status:** Proposed  
**Date:** 2026-06-06

## Context

The ESAA paper requires that multiple concurrent agents serialize safely at the event level. Two classes of concurrency exist in Kando:

1. **Multiple independent runs** (different `run_id`s): already safe — each run has its own `MemoryLedgerStore` or EventStoreDB stream. No shared state exists between runs (after ADR-008 fixed the global counter).

2. **Multiple agents on the same run** (shared ledger): not implemented. Two agents appending to the same `MemoryLedgerStore` simultaneously will race.

The `EventStreamLedgerStore` currently uses `StreamState.ANY` for all appends, bypassing EventStoreDB's optimistic concurrency control (OCC). This means two concurrent writers can both succeed, producing an interleaved stream with no conflict detection.

## Current State

`MemoryLedgerStore.append()` is protected by a `threading.Lock` (added in the gap-fixing pass). This makes it thread-safe for single-process concurrent runs. However, there is no conflict detection — two agents can append conflicting events without either knowing.

## Proposed Decision

For the EventStoreDB backend:
1. Replace `StreamState.ANY` with `current_version=self._known_version` in every `append()` call.
2. Handle `WrongExpectedVersion` by re-reading the stream, re-applying the missed events to the world, and retrying the append (optimistic concurrency retry loop).
3. Track `_known_version` as an instance variable, updated after each successful append.

For `MemoryLedgerStore`, the `threading.Lock` is sufficient for single-process use. For true multi-agent safety (multiple processes), use the EventStoreDB backend.

For multi-agent within a single run, define a `MultiAgentRuntime` that spawns multiple `Runtime` instances sharing one `LedgerStore`, with a coordinator that merges their event queues via a priority queue ordered by timestamp.

## Consequences

**Positive:**
- EventStoreDB's OCC provides the serialization guarantee ESAA requires: no two agents can simultaneously commit conflicting events.
- Retry-on-conflict is the standard approach in event-sourced systems and is well-understood.

**Negative:**
- Retry loops add latency under contention. High-contention runs (many agents on one stream) will degrade.
- The `MultiAgentRuntime` design is non-trivial — defining what "conflicting events" means in the domain requires domain-specific conflict resolution logic.

## Not Yet Implemented
