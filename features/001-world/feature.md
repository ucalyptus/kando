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
- DAE coverage: ✅ feature.md ✅ acs.md (31 ACs) ✅ spec.md (34 scenarios) ✅ acceptance tests (210/210)
- Mutation score: 95.4% (188/197) on `kando/world/` — above 0.80 charter threshold
- Completed: 2026-06-06 — all checkpoints CP0–CP8 done
- Linear: SAY-5 closed
