# Core Concepts

## Vocabulary

| Kando term | What it is |
|---|---|
| **Ledger** | The append-only event log for a single agent run. One ledger per run. The source of truth. |
| **World** | The live projected state: all objects, relations, and their current data. Deterministically derived from the ledger. Never stored directly — always reconstructable. |
| **Responder** | A function (plain, LLM-backed, or tool-calling) that subscribes to event patterns, reads the world, and emits new events back to the ledger. Responders do not call each other. |
| **Edge logic** | Semantic behavior attached to a typed relation (`contradicts`, `depends_on`, `supports`, `blocks`). When the relation is created, its edge logic fires. Coordination without orchestration. |
| **Snapshot** | A materialized checkpoint of the world at a ledger position. Optimization for fast startup — the ledger remains authoritative. |
| **Branch** | A fork of a ledger at a specific position. The prefix before the branch point is shared (zero-copy, no re-execution). Each branch diverges independently. |
| **Diff** | A structural comparison of two worlds (typically parent vs. branch) showing which objects, relations, and responder outputs diverged. |
| **Cache** | Content-addressed store of LLM responses keyed by normalized request hash. On replay or branch, cached responses are served instead of making new API calls. |
| **Kit** | A domain bundle: object types, responders, tools, prompts, and policies packaged for a specific use case (diligence, research, planning). |
| **Trace** | The causal chain from any event back to the originating goal. Every event records its parent event and the responder that emitted it. |
| **Budget** | Per-run resource limits: max events, max LLM cost, max wall-clock seconds, max recursion depth. Enforced by the runtime, not by individual responders. |

---

## Design Principles

### The ledger is the agent

There is no separate "memory," no mutable state store, no conversation context that outlives its events. If it didn't happen in the ledger, it didn't happen.

### The world is derived, never stored

Object data, relation graphs, responder state — all of it is a deterministic function of the ledger. Snapshots are a performance optimization. The ledger can always reconstruct the world from scratch.

### Responders are physics, not control flow

A responder subscribes to a pattern. When the pattern matches, the responder fires. There is no orchestrator deciding what runs next. Chaining happens because one responder's output event matches another responder's subscription. The execution order is an emergent property of the event stream.

### Edge logic carries meaning

A `contradicts` relation is not just data — it's a trigger. When evidence contradicts a belief, the contradiction-resolution responder fires automatically. Logic lives where the semantic meaning is, not in a central router.

### Branches are cheap

Forking a 500-event run at position 250 replays the first 250 events from cache (zero LLM calls, sub-second) and executes only the divergent tail. This makes hypothesis testing, A/B comparison, and self-improvement loops economically viable.

### Traces are not observability

The causal chain from goal to artifact is not a debugging tool bolted on after the fact. It is the structural output of every run, queryable at any time, and it falls out of the architecture for free.

---

## Event model

Every `KandoEvent` carries:

```python
@dataclass
class KandoEvent:
    id: str           # unique within the ledger
    type: str         # e.g. "object.created", "relation.created"
    source: str       # ledger identity — "run:{id}" or "branch:{id}"
    actor: str        # which responder emitted this event
    cause: list[str]  # parent event IDs — the causal chain
    timestamp: datetime
    data: dict        # type-specific payload
```

### Built-in event types

| Type | Meaning |
|---|---|
| `object.created` | A WorldObject was created |
| `object.patched` | A WorldObject's data was partially updated |
| `relation.created` | A typed relation between two objects was created |
| `relation.removed` | A relation was removed |
| `branch.created` | A branch was forked from a parent run |
| `budget.exhausted` | A budget limit was hit; the run stops |
| `llm.request` / `llm.response` | LLM call lifecycle (for cost tracking) |
| `tool.called` / `tool.returned` | Tool invocation lifecycle |
| `responder.fired` / `responder.completed` / `responder.failed` | Responder lifecycle |
| `kit.loaded` | A kit module was loaded by the runtime |

---

## The event loop

```
seed events
    │
    ▼
┌───────────────────────────────────┐
│           Runtime loop            │
│                                   │
│  dequeue event                    │
│     → append to ledger            │
│     → apply to world              │
│     → check budget                │
│     → dispatch edge logic         │
│     → fire matching responders    │
│     → enqueue output events       │
│                                   │
│  repeat until queue empty         │
└───────────────────────────────────┘
    │
    ▼
projected World
```

The loop is synchronous and deterministic. The same seed events through the same responders always produce the same world.
