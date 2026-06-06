# Tutorial 2 — The Ledger Is the Agent

**BLUF: Kando has no "memory" object, no mutable state store, no
conversation buffer. The append-only event log *is* the agent's identity.
If it didn't happen in the ledger, it didn't happen.**

---

## Why this matters

Traditional agent frameworks keep state in mutable objects — a dict of
memories, a vector store, a conversation list. That state is fragile: it
can't be replayed, it can't be forked, and when something goes wrong
you have no causal record of how you got there.

Kando replaces all of that with a single append-only log (the **ledger**).
Everything the agent knows is an event. Everything the agent has done is
an event. The "world" is just a read-through cache computed from the log.

---

## The three primitives

### 1. KandoEvent — the atomic unit

Every event has the same shape:

```python
@dataclass
class KandoEvent:
    id: str           # unique identifier
    type: str         # e.g. "object.created", "llm.response"
    source: str       # which ledger ("run:abc123")
    actor: str        # which responder emitted this
    cause: list[str]  # parent event IDs — the causal chain
    timestamp: datetime
    data: dict        # payload (object data, LLM messages, etc.)
```

Events are **immutable**. Once appended, they never change. An
`object.patched` event does not mutate the original — it records a new
fact that the projection applies on top.

### 2. Ledger — the append-only log

```python
class LedgerStore(Protocol):
    def append(self, events: list[KandoEvent]) -> None: ...
    def read_all(self) -> Iterator[KandoEvent]: ...
    def read(self, from_position: int) -> Iterator[KandoEvent]: ...
    def stream_name(self) -> str: ...
```

Two implementations ship with Kando:

| Backend | When to use |
|---|---|
| `MemoryLedgerStore` | Development, tests, demos. Events vanish on exit. |
| `EventStreamLedgerStore` | Production. Backed by EventStoreDB. Durable, replayable. |

The runtime picks automatically: if `EVENTSTORE_URL` is set, you get
EventStoreDB. Otherwise, in-memory.

### 3. World — the derived projection

```python
class World:
    objects: dict[str, WorldObject]
    relations: dict[str, Relation]
    context: dict[str, Any]
```

The world is **never stored**. It is always reconstructed from the ledger
using `reproject(ledger)`:

```python
from kando.world.projection import reproject

world = reproject(ledger)
# world.objects and world.relations are now populated
```

This means:

- **Replaying** the ledger always produces the same world.
- **Snapshots** are an optimization — the ledger is authoritative.
- **Deleting** or "forgetting" data means appending a new event, not
  mutating old ones.

---

## Seeing it in practice

```bash
# 1. Run a kit
.venv/bin/python -m kando.cli.main run kits/diligence --goal "Evaluate Stripe"

# 2. The output shows events AND the world derived from them
#    Events = the ledger (source of truth)
#    Objects/Relations = the world (derived)
```

The events you see in the output are the *actual ledger contents*. The
objects and relations at the bottom are the projection — what you get when
you replay those events from scratch.

---

## Mental model

```
Events (append-only)          World (derived, ephemeral)
┌─────────────────────┐       ┌────────────────────────┐
│ object.created  e0  │──────▶│ Company "Stripe"       │
│ object.created  e1  │──────▶│ Claim "pending..."     │
│ relation.created e2 │──────▶│ Claim ──supports──▶ …  │
│ llm.request     e3  │       │                        │
│ llm.response    e4  │──────▶│ Claim patched w/ text  │
└─────────────────────┘       └────────────────────────┘
         ▲                              ▲
    source of truth              computed on demand
    survives restart             rebuilt from ledger
```

---

## Key takeaways

- The ledger is append-only. No updates, no deletes.
- The world is deterministically derived — `reproject(ledger)` always
  produces the same result.
- Every event records its causal parent, so you always know *why*
  something exists.
- This architecture makes replay, fork, and diff possible for free.

---

**Next:** [Tutorial 3 — Responders and Reactive Chains](03-responders.md)
