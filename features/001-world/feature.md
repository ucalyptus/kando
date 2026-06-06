# Feature 001 — World (Deterministic Projected State)

## What it is
The World is the live projected state of a kando run — all objects and typed
relations derived deterministically from the event ledger. It is never stored
directly; it is always reconstructable by replaying events.

## Why it matters
Every responder reads the World to decide what to emit next. The World must be
deterministic (same ledger → same world), consistent (all projections agree),
and efficient (incremental apply for each new event).

## Code locations
- `kando/world/graph.py` — `WorldObject`, `WorldRelation`, `World` dataclasses
- `kando/world/projection.py` — `project()`, `apply()`, `reproject()`
- `kando/world/snapshot.py` — snapshot materialization

## Existing test material
- `features/world.feature` — BDD scenarios (creating, patching, removing objects + relations)
- `features/steps/world_steps.py` — step implementations
- `tests/test_snapshot.py` — snapshot unit tests
- `tests/test_properties.py` — Hypothesis property tests

## Status
- DAE coverage: ❌ feature.md ❌ acs.md ❌ spec.md ❌ acceptance tests
- Existing tests: BDD feature file + snapshot unit tests (in flat layout)
- Next step: `/engineer.discover-acs` (reverse-engineer mode) to extract acs.md
