# Architecture

## System overview

```
┌──────────────────────────────────────────────────────────────┐
│                         Kando Runtime                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                    Agent Layer                         │  │
│  │                                                        │  │
│  │  Kits ─── Responders ─── Edge Logic ─── LLM Cache     │  │
│  │                                                        │  │
│  │  World (projected state: objects + typed relations)     │  │
│  │  Branch engine (fork, replay shared prefix, diff)      │  │
│  │  Trace engine (causal lineage queries)                 │  │
│  │  Budget enforcement (event/cost/time caps)             │  │
│  └──────────┬─────────────────────────┬───────────────────┘  │
│             │ append events           │ read events / views   │
│             ▼                         ▼                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                   Event Substrate                      │  │
│  │                                                        │  │
│  │  Ledgers:    run:{id}         (per-run event log)      │  │
│  │              branch:{id}      (forked runs)            │  │
│  │                                                        │  │
│  │  Delivery:   DeliveryBus      (in-process subscribers) │  │
│  │  Snapshot:   world checkpoints (JSON, disk)            │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## Data flow

```
Goal (text)
  │
  ▼
seed_from_goal()  ──►  KandoEvent(type="object.created", data={...})
                                    │
                                    ▼
                             Runtime.run(seed_events)
                                    │
                      ┌─────────────┼──────────────┐
                      ▼             ▼               ▼
                   Ledger        World          Budget
                 .append()     .apply()        .check()
                      │             │               │
                      └─────────────┘               │
                                    │               │ exhausted?
                             Responders             │
                             (matching)        stop loop
                                    │
                             output events
                                    │
                              back to queue
```

---

## Layer responsibilities

### Ledger (storage)

- Append-only, ordered, durable event stream
- One stream per run: `run:{run_id}`
- Branched runs use their own stream: `branch:{branch_id}`
- Backend: EventStoreDB (durable) or in-memory (transient)
- Interface: `LedgerStore.append()` / `LedgerStore.read()`

### World (state)

- Deterministic projection of the ledger
- Never persisted — always reconstructable from events
- Contains `objects: dict[str, WorldObject]` and `relations: dict[str, Relation]`
- Also holds `context: dict` for runtime-level shared state (e.g., LLM cache)
- Projection: `apply(world, event)` handles `object.created`, `object.patched`, `relation.created`, `relation.removed`

### Responders (logic)

- `fn(event: KandoEvent, world: World) -> Iterator[KandoEvent]`
- Subscribe to a `pattern: frozenset[str]` of event types
- Empty pattern = match all event types (wildcard, used by delivery bus)
- No side effects except emitting events — responders do not call each other

### Edge logic (semantic reactions)

- Registered per relation type: `@edge_logic("contradicts")`
- Fires automatically when a `relation.created` event has `data.type == "contradicts"`
- Allows kits to encode domain semantics at the schema level

### Budget (safety)

- `Budget(max_events, max_llm_cost_usd, max_wall_seconds, max_recursion_depth)`
- `BudgetEnforcer` tracks cumulative usage and emits `budget.exhausted` when any limit is hit
- Recursion depth is tracked via causal lineage: `depth[event] = max(depth[cause] for cause in event.cause) + 1`

### Branch / Fork / Diff

- Fork: copy a prefix of the parent ledger to a new branch stream; write `branch.created` marker
- Diff: reproject both ledgers, compare `WorldDiff(added_objects, removed_objects, patched_objects, added_relations, removed_relations)`
- Replay: permissive (reproject as-is) or strict (re-fire responders from seed events)

---

## Module layout

```
kando/
  cli/main.py          ← all CLI commands
  ledger/
    interface.py       ← LedgerStore ABC
    memory.py          ← MemoryLedgerStore (in-process)
    stream.py          ← EventStreamLedgerStore (EventStoreDB)
  world/
    graph.py           ← World, WorldObject, Relation
    projection.py      ← project(), apply(), reproject()
    snapshot.py        ← save_snapshot(), load_snapshot()
  responders/
    base.py            ← Responder, ResponderRegistry
    budget.py          ← Budget, BudgetEnforcer
    delivery.py        ← DeliveryBus, create_delivery_responder()
    edge.py            ← edge_logic decorator, dispatch()
  cache/llm.py         ← LLMCache, ScopedLLMCache
  trace/lineage.py     ← build_lineage_index(), explain()
  branch/
    fork.py            ← BranchMeta, fork()
    replay.py          ← read_branch()
    diff.py            ← WorldDiff, diff()
  mcp/server.py        ← MCP tool server (5 tools)
  schema/events.py     ← KandoEvent, event type constants
  runtime.py           ← Runtime (main event loop)

kits/
  diligence/kit.py     ← Company/Claim/Evidence/Contradiction/Report
  research/kit.py      ← Goal/Question/Finding/Synthesis
```
