---
ac_count: 31
high_priority_count: 15
discovered: "2026-06-06"
mode: reverse-engineer
source_material:
  - features/world.feature
  - features/steps/world_steps.py
  - tests/test_snapshot.py
  - tests/test_properties.py
  - kando/world/graph.py
  - kando/world/projection.py
  - kando/world/snapshot.py
---

# Acceptance Criteria — 001-world (Deterministic Projected State)

The World is the live view of a kando run derived solely from the event ledger.
It is never stored directly; it is always reconstructable by replay.
All ACs are stated in terms of observable World state — never implementation detail.

---

## AC-1: Object creation
**Priority:** High  
**Type:** Happy path  

When an `object.created` event is applied, the world gains a new object carrying the
id, type, and data from that event. A subsequent lookup by that id finds the object
with its data intact.

---

## AC-2: Object patch
**Priority:** High  
**Type:** Happy path  

When an `object.patched` event is applied to an object that exists, the patch values
are merged into the object's data (new keys are added, existing keys are overwritten
by the patch). Keys not mentioned in the patch are preserved.

---

## AC-3: Relation creation
**Priority:** High  
**Type:** Happy path  

When a `relation.created` event is applied, the world gains a named relation carrying
its id, type, source object id, target object id, and optional data. The relation
is retrievable by id and appears in lookups for either of its endpoint objects.

---

## AC-4: Relation removal
**Priority:** High  
**Type:** Happy path  

When a `relation.removed` event is applied, the named relation is no longer present
in the world. A lookup for it returns nothing.

---

## AC-5: Budget exhaustion signal
**Priority:** High  
**Type:** Happy path  

When a `budget.exhausted` event is applied, the world records that the run's budget
is exhausted. Responders that read this signal will observe it in the world's runtime
context.

---

## AC-6: Full projection from event stream
**Priority:** High  
**Type:** Happy path  

Projecting an ordered event stream produces a world that faithfully reflects every
event applied in sequence. The resulting world contains exactly the objects and
relations that the stream described.

---

## AC-7: Single-event in-place application
**Priority:** High  
**Type:** Happy path  

A single event can be applied directly to an existing world. The world is mutated in
place to reflect that event. Nothing is returned.

---

## AC-8: Ledger reproject
**Priority:** High  
**Type:** Happy path  

The world can be rebuilt at any time by reading all events from a ledger store and
projecting them in order. The result is a complete, fresh world — equivalent to
projecting those same events from an empty starting state.

---

## AC-9: Object lookup
**Priority:** High  
**Type:** Happy path  

A single object can be retrieved from the world by id. If the id is present, the
full object (id, type, data) is returned. If no object with that id exists, nothing
is returned (not an error).

---

## AC-10: Relation lookup
**Priority:** High  
**Type:** Happy path  

All relations whose source or target is a given object id can be retrieved in a
single call. An optional relation-type filter narrows the result to relations of
that type only. When nothing matches, an empty list is returned.

---

## AC-11: Snapshot roundtrip
**Priority:** High  
**Type:** Happy path  

A world can be checkpointed by saving it together with the current ledger position.
Loading that checkpoint returns the same world state (all objects with their data,
all relations with their endpoint ids and data) and the same position. Nothing is
lost in the roundtrip.

---

## AC-12: Snapshot directory configured by environment
**Priority:** Medium  
**Type:** Happy path  

The directory where snapshots are written is controlled by the `KANDO_SNAPSHOT_DIR`
environment variable. When the variable is unset, snapshots go to `.kando_snapshots`
in the working directory.

---

## AC-13: Missing snapshot returns nothing
**Priority:** High  
**Type:** Edge case  

Loading a snapshot for a run that has never been checkpointed returns nothing. This
is not an error — the caller is expected to fall back to full replay.

---

## AC-14: Snapshot directory auto-created
**Priority:** Medium  
**Type:** Edge case  

If the snapshot directory does not exist when a snapshot is saved, it is created
automatically. Callers do not need to create it in advance.

---

## AC-15: Snapshot overwrite
**Priority:** Medium  
**Type:** Edge case  

Saving a snapshot for a run id that already has a snapshot replaces the previous
checkpoint. The load that follows reflects only the latest save.

---

## AC-16: Object creation replaces existing object (upsert)
**Priority:** High  
**Type:** Edge case  

When an `object.created` event is applied for an id that already exists in the
world, the existing object is replaced by the new one. The world faithfully reflects
the event stream — the caller who emitted the event intended the replacement.
(Contrast with patching a non-existent object, which is a no-op; see AC-17.)

---

## AC-17: Patching a non-existent object is a no-op
**Priority:** High  
**Type:** Edge case  

When an `object.patched` event references an id that is not in the world, the world
is unchanged. No error is raised. This is a deliberate design choice: partial
projections and replay windows may apply patches before the creation event arrives,
and the World must not crash.

---

## AC-18: Removing a non-existent relation is a no-op
**Priority:** Medium  
**Type:** Edge case  

When a `relation.removed` event references an id that is not in the world, the world
is unchanged. No error is raised.

---

## AC-19: Dangling relations are allowed
**Priority:** High  
**Type:** Edge case  

A `relation.created` event may reference source or target object ids that do not
currently exist in the world. The relation is stored regardless. The World does not
enforce referential integrity — that is the responsibility of responders that read
the relation. This matters for partial projections and replay windows where objects
and relations may arrive out of dependency order.

---

## AC-20: Empty event stream yields empty world
**Priority:** Medium  
**Type:** Edge case  

Projecting an empty event list produces a world with no objects and no relations.

---

## AC-21: Missing data field defaults to empty dict
**Priority:** Medium  
**Type:** Edge case  

An `object.created` or `relation.created` event that omits the `data` field produces
an object or relation whose data is an empty dict. This is not an error.

---

## AC-22: Projection is deterministic
**Priority:** High  
**Type:** Determinism  

The same ordered event sequence, projected any number of times, always produces
identical worlds. The projection function has no hidden state, randomness, or
time-dependent behavior.

---

## AC-23: Projection is order-independent for independent creation events
**Priority:** Medium  
**Type:** Determinism  

A stream consisting entirely of `object.created` events for distinct ids produces
the same world regardless of the order those events appear in. Objects do not
depend on each other, so ordering among them is irrelevant.

---

## AC-24: Object data is preserved exactly
**Priority:** Medium  
**Type:** Determinism  

The data stored on an object in the projected world is byte-for-byte identical to
the data carried by the `object.created` event. No values are lost, coerced, or
added.

---

## AC-25: Apply is isolated from event mutation
**Priority:** High  
**Type:** Determinism  

Applying an event copies its data into the world. Subsequent changes to the event's
data dict after `apply()` returns do not affect the world. The world owns its data.

---

## AC-26: Unknown event types are silently skipped
**Priority:** Medium  
**Type:** Error  

When `apply()` receives an event whose type is not in the handled set (e.g.
`responder.fired`, `llm.request`, `kit.loaded`), the world is left unchanged and no
error is raised. The event is dropped.

---

## AC-27: Corrupt or unreadable snapshot returns nothing
**Priority:** High  
**Type:** Error  

If a snapshot file exists but cannot be parsed (malformed JSON, missing required
keys, wrong structure), `load_snapshot` returns nothing — the same result as a
missing file. It does not propagate the error. A snapshot is a performance
optimization; the source of truth is the ledger. Callers fall back to full replay.

---

## AC-28: World context is not persisted in snapshots
**Priority:** Medium  
**Type:** Cross-cutting  

The world's runtime context (e.g. `budget_exhausted`) is not written to or read
from the snapshot file. After loading a snapshot, the context is always empty.
Responders that depend on context signals must receive them from events played after
the snapshot position.

---

## AC-29: Per-run-id snapshot isolation
**Priority:** Medium  
**Type:** Cross-cutting  

Each run's snapshot is stored as a separate file keyed by run id. Saving a snapshot
for one run does not affect any other run's snapshot.

---

## AC-30: Snapshot file format is plain JSON
**Priority:** Low  
**Type:** Cross-cutting  

The snapshot file is a valid JSON document with a top-level `"world"` object
(containing `"objects"` and `"relations"` as lists) and a top-level `"position"`
integer. The format is human-readable and inspectable without tooling.

---

## AC-31: Empty world snapshots cleanly
**Priority:** Low  
**Type:** Cross-cutting  

A world with no objects and no relations can be saved and reloaded. The restored
world has empty object and relation collections and the correct position.
