# Branch & Diff

Branching lets you fork a run at any ledger position and explore an alternative timeline. The shared prefix costs nothing to re-execute.

## BranchMeta

::: kando.branch.fork.BranchMeta
    options:
      show_source: true
      heading_level: 3

::: kando.branch.fork.fork
    options:
      show_source: true
      heading_level: 3

---

## WorldDiff

::: kando.branch.diff.WorldDiff
    options:
      show_source: true
      heading_level: 3

::: kando.branch.diff.diff
    options:
      show_source: true
      heading_level: 3

---

## Forking via CLI

```bash
# Requires EVENTSTORE_URL
export EVENTSTORE_URL=http://localhost:2113

kando fork abc123def456 --at 2
# → Branch ID  : 789ghi012jkl
# → Parent run : abc123def456
# → Fork at    : 2  (shared prefix: 2 events)
```

## Diffing via CLI

```bash
kando diff abc123def456 789ghi012jkl
# → Diff: abc123def456 -> 789ghi012jkl
# → Summary: +1 objects
#   + object  new-claim-id  {'text': 'New finding', ...}
```

## Programmatic branching

```python
from kando.branch.fork import BranchMeta, fork
from kando.branch.diff import diff as world_diff
from kando.world.projection import reproject

# Create branch metadata
meta = fork(parent_run_id="abc123", fork_position=2, branch_id="xyz789")

# Compare two worlds
store_a = EventStreamLedgerStore("abc123")
store_b = EventStreamLedgerStore("xyz789")
world_a = reproject(store_a)
world_b = reproject(store_b)

d = world_diff(world_a, world_b)
print(d.summary())         # "+2 objects, +1 relations"
print(bool(d))             # True if any changes
print(d.added_objects)     # list of new object IDs
print(d.patched_objects)   # list of modified object IDs
```

## Branch replay

```python
from kando.branch.replay import read_branch

# Yield prefix from parent + branch tail
events = list(read_branch(meta, parent_store, branch_store))
```

## Why branching is cheap

The branch stream contains only the events *after* the fork position. The shared prefix is referenced by position — the parent's events are not copied. When projecting a branch:

1. Read events `0..fork_position` from the parent ledger
2. Read all events from the branch ledger (the divergent tail)
3. Project the concatenated stream

No LLM calls are made for the shared prefix on branch projection.
