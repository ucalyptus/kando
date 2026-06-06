# ADR-003: World as Deterministic Projection

**Status:** Accepted  
**Date:** 2026-06-06

## Context

The world (objects + relations) must be reconstructible from the event log. Two strategies were considered:

1. **Reactive substrate**: the world is a live reactive graph; behaviors fire when nodes/edges change (the "ActiveGraph" design from arXiv 2605.21997).
2. **Pure projection**: the world is derived by a pure fold over the event stream; behaviors fire on events, not on graph mutations.

## Decision

The world is a pure deterministic projection. `project(event_stream) → World` is a pure function. `apply(world, event)` applies a single event in-place. There is no reactivity in the world graph itself — it is a dumb data structure. Behaviors (responders) fire on events, not on world changes.

Events are applied to the world via `deepcopy` to prevent aliasing: `WorldObject.data` is a deep copy of `event.data["data"]`, ensuring events remain immutable records after being applied.

## Consequences

**Positive:**
- `project()` is trivially testable: deterministic, no side effects.
- `reproject(ledger)` is the canonical way to load any world state from scratch.
- Snapshot integration is straightforward: project up to position N, save snapshot, replay delta from N.
- No hidden reactive triggers — the world is passive data.

**Negative:**
- One level removed from the paper's ActiveGraph design: behaviors fire on events, not graph mutations. This means a behavior that wants to react to "a new edge between X and Y" must do so by observing the `RELATION_CREATED` event, not by watching the graph.
- Full reproject on every `runtime.load()` is O(n) in ledger length. Snapshot integration (not yet implemented) would reduce this to O(delta).

## Known Gap (Forward-Looking)

Snapshot integration: `Runtime.load()` should load the latest snapshot and replay only the delta from the snapshot position. See ADR-012 for hash-verified replay, which is a prerequisite.
