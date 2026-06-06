# Tutorial 4 — Branching and Diffing

**BLUF: Fork any run at any ledger position. The shared prefix is
zero-copy (no re-execution). Each branch diverges independently. Diff two
branches to see exactly what changed — added, removed, or patched objects
and relations.**

---

## Why this matters

Hypothesis testing is expensive in most agent systems — you re-run the
whole thing from scratch. In Kando, the event log makes forking cheap:
events before the fork point are shared. Only the divergent tail runs new
logic or new LLM calls.

---

## Prerequisites

Branching and diffing require **durable storage**. Start EventStoreDB:

```bash
docker compose up -d eventstore
export EVENTSTORE_URL=http://localhost:2113
```

---

## Step 1 — Create a base run

```bash
kando run kits/diligence --goal "Evaluate Stripe"
```

Note the **Run ID** from the output (e.g., `a1b2c3d4e5f6`).

## Step 2 — Fork the run

Fork at position 2 (keep the first two events, diverge from there):

```bash
kando fork a1b2c3d4e5f6 --at 2
```

Output:

```
Branch ID    : x9y8z7w6v5u4
Parent run   : a1b2c3d4e5f6
Fork position: 2  (shared prefix: 2 events)
```

The branch has its own ledger (`branch:x9y8z7w6v5u4`) that starts with
the same two events as the parent. From position 2 onward, it's
independent.

## Step 3 — Diff the two branches

```bash
kando diff a1b2c3d4e5f6 x9y8z7w6v5u4
```

Output shows structural differences:

```
Diff: a1b2c3d4e5f6 -> x9y8z7w6v5u4
Summary: 2 added, 0 removed, 1 patched objects; 1 added, 0 removed relations
  + object  claim-newclaim  {'text': '...', 'status': 'pending'}
  ~ object  claim-original  {'status': 'pending'} -> {'status': 'complete'}
  + relations: ['rel-supports-abc12345']
```

---

## How it works internally

### Fork

1. Read all events from the parent ledger up to position N.
2. Append that prefix to a new branch ledger (zero LLM cost — events are
   already computed).
3. Append a `branch.created` event recording the fork metadata.

```python
# Simplified from kando/cli/main.py cmd_fork
prefix = list(parent_store.read(from_position=0))[:fork_position]
branch_store.append(prefix)
branch_store.append([branch_created_event])
```

### Diff

1. Reproject both ledgers into separate worlds.
2. Compare the two world graphs — objects and relations.

```python
from kando.branch.diff import diff as world_diff

world_a = reproject(ledger_a)
world_b = reproject(ledger_b)
d = world_diff(world_a, world_b)
# d.added_objects, d.removed_objects, d.patched_objects
# d.added_relations, d.removed_relations
```

---

## Use cases

| Scenario | How to use branching |
|---|---|
| **A/B testing prompts** | Fork before the `llm.request` event, re-run with a different kit or model |
| **What-if analysis** | Fork at the point of a key decision, explore the alternative |
| **Rollback** | Fork at a known-good position, discard the bad branch |
| **Self-improvement** | Fork, run a refinement responder, diff to measure improvement |

---

## Key takeaways

- Fork is cheap — shared prefix means zero re-execution.
- Diff is structural — you see exactly which objects and relations changed.
- Branching requires EventStoreDB (durable ledger).
- Every branch is a first-class ledger with its own identity.

---

**Next:** [Tutorial 5 — Tracing Causality](05-tracing-causality.md)
