---
slug: 001-world
checkpoint: 4
plan_status: approved
created: "2026-06-06"
mode: reverse-engineer
---

# Plan — 001-world (Deterministic Projected State)

## Architecture

### Components

| Module | Role | Dependencies |
|---|---|---|
| `kando/world/graph.py` | Pure data model — `WorldObject`, `Relation`, `World` | stdlib only |
| `kando/world/projection.py` | Event→World reduction: `project()`, `apply()`, `reproject()` | `graph.py`, `kando.schema.events` |
| `kando/world/snapshot.py` | Disk checkpoint: `save_snapshot()`, `load_snapshot()` | `graph.py`, stdlib (`json`, `os`, `pathlib`) |

### Data flow

```
LedgerStore ──read_all()──► event stream ──project()──► World
                                                          │
                                                    save_snapshot()
                                                          │
                                               {run_id}.json (plain JSON)
                                                          │
                                                    load_snapshot()
                                                          │
                                                   World + position
```

### Key design decisions

| Decision | Rationale | AC |
|---|---|---|
| `copy.deepcopy` in `apply()` | World owns its data; caller mutation of the event dict after `apply()` must not corrupt the world | AC-25 |
| No referential integrity on relations | Partial projections and replay windows may apply relation events before object events; the World must not crash | AC-19 |
| `object.created` is upsert | Event stream is the source of truth; re-creation replaces (mirrors ledger semantics) | AC-16 |
| World context not persisted in snapshots | Context (`budget_exhausted`, etc.) is ephemeral runtime state, not part of the durable world model | AC-28 |
| `load_snapshot` returns `None` on any error | Snapshot is a performance cache; the ledger is the source of truth; callers always have a fallback | AC-27 |
| `KANDO_SNAPSHOT_DIR` env controls snapshot path | Makes snapshot location testable and deployable without code changes | AC-12 |

### Coupling boundaries

- `graph.py` has **zero external deps** — safe to import anywhere, trivial to test, easy to serialise.
- `projection.py` couples to `kando.schema.events` for event type constants — the only dependency outside `world/`.
- `snapshot.py` has no HTTP, no subprocess I/O — fully synchronous file reads/writes.

---

## Charter Check

| Rule | Verdict | Notes |
|---|---|---|
| `feature.md` + `acs.md` + `spec.md` + passing acceptance tests before merge | ✅ | All present; 204 tests pass on `world` branch |
| Mutation testing on `kando/world/` (threshold ≥ 0.80) | ⚠️ | Not yet run — see Amendment A1 |
| No broken tests on `main` | ✅ | 204 pass on `world` branch; no regression on `main` |
| No comments unless WHY is non-obvious | ✅ | One module docstring in `snapshot.py`; no inline clutter |
| No abstractions for single-use code | ✅ | Three focused modules; no speculative additions |
| Touch only what the task requires | ✅ | Only `snapshot.py` patched (AC-27 fix) during CP2–CP3 |
| Tests in `tests/`; acceptance in `features/NNN-slug/` | ✅ | `tests/test_snapshot.py`, `tests/test_properties.py`; `features/001-world/spec.md` |
| Commits co-authored by Claude | ✅ | All commits on `world` branch carry co-author trailer |
| Autonomy stance: low-to-medium | ✅ | No external API calls with real cost; no destructive git ops without request |
| Performance budgets (required at high autonomy only) | ✅ N/A | Not required at low-to-medium; see Performance section |

### Amendments

**A1 — Deferred mutation hardening**

Mutation testing for `kando/world/` is deferred to Phase 2. The code was implemented before DAE onboarding (reverse-engineer mode); all 34 spec scenarios pass and form the spec contract going forward. The mutation run is blocked only by sequencing — it belongs in CP7 (Verify), not CP4. This amendment commits: `atdd:kill-mutants` runs on `kando/world/` before the feature is promoted to `done` in the manifest and merged to `main`. If the kill score is below 0.80, missing coverage is added as new spec scenarios before merge.

---

## Phasing

### Phase 1 — Spec-compliance pass (complete)

Code, tests, and DAE artifacts all exist and are consistent. No implementation work remains.

Artifacts complete:
- `kando/world/graph.py` — `WorldObject`, `Relation`, `World`
- `kando/world/projection.py` — `project()`, `apply()`, `reproject()`
- `kando/world/snapshot.py` — `save_snapshot()`, `load_snapshot()` (AC-27 fix applied)
- `features/001-world/feature.md`, `acs.md`, `spec.md`
- `features/steps/world_spec_steps.py` — 34 scenarios, all green
- `tests/test_snapshot.py`, `tests/test_properties.py`

### Phase 2 — Mutation hardening

Run `atdd:kill-mutants` against `kando/world/` (Charter threshold: ≥ 0.80).

Expected survivors: none — the 34 scenarios cover all four event handler branches, both snapshot paths (save/load), the deepcopy isolation, the no-op patch and remove cases, and the None-on-error fallback.

If kill score < 0.80: identify surviving mutants, add targeted scenarios to `spec.md`, re-run. Each new scenario maps to the existing or a new AC.

### Phase 3 — Merge and close

Once mutation score ≥ 0.80:
- Open PR: `world` → `main`
- Update manifest: `001-world` status → `done`
- Update Linear SAY-5 with CP4–CP7 completion
- Delete `world` branch post-merge

---

## Performance budgets

`feature.md` does not set a `validation_method` — standard DAE stack applies.

| Operation | Complexity | Constraint |
|---|---|---|
| `project(stream)` | O(n events) | No explicit SLA; bounded by run budget (responder limit) |
| `apply(world, event)` | O(1) | Dict insert/update; `copy.deepcopy` is bounded by event data size |
| `save_snapshot()` | O(\|objects\| + \|relations\|) | File write; acceptable at current run scales |
| `load_snapshot()` | O(\|objects\| + \|relations\|) | File read + JSON parse; called once at run startup |
| `get_relations(obj_id)` | O(\|relations\|) | Linear scan; acceptable until relation counts reach ~10k |

No explicit latency budget is required at low-to-medium autonomy. If the linear scan in `get_relations` becomes a bottleneck (e.g. kits produce thousands of relations), the fix is an adjacency index on `World` — that belongs in a future feature, not here.

---

## Collaboration schedule

| Step | Owner | Trigger |
|---|---|---|
| Architecture confirmation | **Human** | This turn (CP4 gate) |
| Mutation run (`atdd:kill-mutants`) | Agent | Phase 2 start |
| Add missing scenarios if kill < 0.80 | Agent proposes → **Human** confirms | If score below threshold |
| PR review + merge | **Human** | Phase 3 |
| Linear SAY-5 close | Agent | Post-merge |

---

## Execution modes

```bash
# Run acceptance spec (34 scenarios)
python3 -m pytest features/steps/world_spec_steps.py -q

# Run full suite (204 tests including unit + Hypothesis)
python3 -m pytest tests/ features/steps/ -q

# Phase 2: mutation hardening
python3 -m mutmut run --paths-to-mutate kando/world/
python3 -m mutmut results
```

---

## Test strategy

`validation_method` is absent from `feature.md` — standard DAE stack applies.

**Acceptance (CP3, complete):** 34 Gherkin scenarios in `features/001-world/spec.md`, exercised via `features/steps/world_spec_steps.py`. All 34 pass. Scenarios cover all 31 ACs: happy path (AC-1–12), edge cases (AC-13–21), determinism (AC-22–25), errors (AC-26–27), cross-cutting (AC-28–31).

**Unit (existing):** `tests/test_snapshot.py` (snapshot roundtrip, directory creation, overwrite) and `tests/test_properties.py` (Hypothesis: determinism, data isolation). These run alongside the BDD spec; total 204 pass.

**Mutation (Phase 2):** `atdd:kill-mutants` on `kando/world/` — target kill score ≥ 0.80 per Charter. Any surviving mutant that is not killed by the current spec triggers a new targeted scenario before merge.

**No integration tests needed:** World is pure in-memory with file I/O only for snapshots; there is no HTTP surface, no subprocess, and no external dependency to stub.
