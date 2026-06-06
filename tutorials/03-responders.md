# Tutorial 3 — Responders and Reactive Chains

**BLUF: A responder is a function that subscribes to an event type, reads
the world, and emits new events. There is no orchestrator. Chains emerge
because one responder's output matches another responder's subscription.**

---

## Why this matters

In most agent frameworks, you write a control flow: "first do X, then
call Y, then decide Z." In Kando, you write *physics*: "whenever this
kind of event happens, do this." The execution order is an emergent
property of the event stream, not a hardcoded sequence.

---

## Anatomy of a responder

```python
from kando.responders.base import Responder
from kando.schema.events import KandoEvent, OBJECT_CREATED, make_event
from kando.world.graph import World
from typing import Iterator

def my_handler(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    # Only react to objects of type "Task"
    if event.data.get("type") != "Task":
        return

    task_id = event.data["id"]
    yield make_event(
        type=OBJECT_CREATED,
        source=event.source,
        actor="my_responder",
        cause=[event.id],        # causal link back to the trigger
        data={
            "id": f"subtask-of-{task_id}",
            "type": "Subtask",
            "data": {"parent": task_id, "status": "pending"},
        },
    )

my_responder = Responder(
    name="my_responder",
    pattern=frozenset({"object.created"}),  # subscribe to this event type
    fn=my_handler,
)
```

Three things to note:

1. **`pattern`** — a frozenset of event types this responder cares about.
   The runtime only calls `handle()` when `event.type in pattern`.
2. **`cause=[event.id]`** — every emitted event records what triggered it.
   This is how traces work.
3. **`yield`** — responders are generators. You can emit zero, one, or
   many events from a single handler invocation.

---

## How chaining works

The runtime processes events from a queue:

```
1. Seed event enters the queue
2. Runtime pops the event, appends it to the ledger, applies it to the world
3. Runtime checks all responders — any whose pattern matches get called
4. Emitted events go back into the queue
5. Repeat until the queue is empty (or budget is exhausted)
```

```python
# Simplified runtime loop (from kando/runtime.py)
while queue:
    event = queue.popleft()
    self._ledger.append([event])
    apply(world, event)

    for r in self._responders:
        if r.matches(event):
            for new_event in r.handle(event, world):
                queue.append(new_event)
```

This means chains are automatic. If responder A emits an `object.created`
event, and responder B subscribes to `object.created`, B fires next —
without A knowing B exists.

---

## Real example: the diligence kit chain

The diligence kit (`kits/diligence/kit.py`) demonstrates a five-step chain:

```
Goal: "Evaluate Acme Corp"

1. CLI emits seed event:   object.created [Company]
2. on_company_created:     object.created [Claim "Pending research..."]
3. on_pending_claim:        llm.request    (asks LLM to research)
4. llm_executor:            llm.response   (LLM reply text)
5. on_llm_response:         object.patched [Claim updated with text]
```

No responder calls another. Each just subscribes to the right event type
and the chain emerges.

---

## Edge logic: relations that trigger behavior

Some relations carry behavior. When a `contradicts` relation is created
between two claims, the edge logic fires automatically:

```python
# kando/responders/edge.py dispatches based on relation type
def dispatch(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    if event.type == "relation.created":
        rel_type = event.data.get("type")
        # fire registered edge handlers for this relation type
```

This is how Kando implements "contradiction resolution" or "dependency
tracking" without a central router.

---

## Try it: minimal responder

Create a file `my_responder_test.py` in the repo root:

```python
from kando.ledger.memory import MemoryLedgerStore
from kando.runtime import Runtime
from kando.responders.base import Responder
from kando.schema.events import KandoEvent, OBJECT_CREATED, make_event
from kando.world.graph import World
from datetime import datetime, timezone
from typing import Iterator

def echo_handler(event: KandoEvent, world: World) -> Iterator[KandoEvent]:
    if event.data.get("type") != "Ping":
        return
    yield make_event(
        type=OBJECT_CREATED,
        source=event.source,
        actor="echo",
        cause=[event.id],
        data={"id": f"pong-{event.data['id']}", "type": "Pong", "data": {}},
    )

ledger = MemoryLedgerStore("test-run")
runtime = Runtime(ledger=ledger, responders=[
    Responder(name="echo", pattern=frozenset({OBJECT_CREATED}), fn=echo_handler),
])

seed = KandoEvent(
    id="ping-1", type=OBJECT_CREATED, source="run:test",
    actor="cli", cause=[], timestamp=datetime.now(timezone.utc),
    data={"id": "ping-1", "type": "Ping", "data": {}},
)

world = runtime.run([seed])
for obj in world.objects.values():
    print(f"  [{obj.type}] {obj.id}")
```

Run it:

```bash
.venv/bin/python my_responder_test.py
```

Expected output:

```
  [Ping] ping-1
  [Pong] pong-ping-1
```

The Ping event caused the Pong event — automatically, with no
orchestration.

---

## Key takeaways

- Responders subscribe to event types, not to other responders.
- Chains are emergent: A's output triggers B if B's pattern matches.
- Every emitted event records its `cause`, creating a full causal graph.
- Edge logic attaches behavior to relations (`contradicts`, `depends_on`).
- The runtime loop is simple: pop → append → project → dispatch → repeat.

---

**Next:** [Tutorial 4 — Branching and Diffing](04-branching-and-diffing.md)
